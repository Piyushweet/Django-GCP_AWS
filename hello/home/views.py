from django.shortcuts import render, HttpResponse, redirect
from google.auth.transport.requests import Request
import google.auth
import asyncio
from googleapiclient import discovery
from google.cloud import compute_v1
from google.auth import compute_engine
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from django.http import HttpResponse
from django.conf import settings
from django.urls import reverse
from pathlib import Path
from django import forms
import boto3


def home(request):
    return render(request, 'index.html')


def aws_button(request):
    # AWS button logic goes here
    return render(request, 'home.html')


def gcp_button(request):
    # AWS button logic goes here
    return render(request, 'home2.html')


def create_vm_gcp(request):
    project_id = 'handliingvm'

    # Build paths inside the project like this: BASE_DIR / ...
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Add the path to your service account key file
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'

    # Load the service account key from the JSON file and create the credentials object
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)

    # Create a Compute Engine client
    compute_client = build('compute', 'v1', credentials=credentials)

    if request.method == 'POST':
        vm_name = request.POST.get('vm_name')
        zone = request.POST.get('zone')
        machine_type = request.POST.get('machine_type')

        try:
            # Create VM configuration
            config = {
                'name': vm_name,
                'machineType': f'zones/{zone}/machineTypes/{machine_type}',
                'disks': [
                    {
                        'boot': True,
                        'autoDelete': True,
                        'initializeParams': {
                            'sourceImage': 'projects/ubuntu-os-cloud/global/images/ubuntu-2004-focal-v20220610',
                        }
                    }
                ],
                'networkInterfaces': [
                    {
                        'network': 'global/networks/default',  # Use the default network
                        'accessConfigs': [
                            {
                                'name': 'External NAT',
                                'type': 'ONE_TO_ONE_NAT'
                            }
                        ]
                    }
                ]
            }

            # Project ID where the VM will be created
            project = project_id  # Do not include 'projects/' in the project ID

            # Create the VM
            operation = compute_client.instances().insert(
                project=project, zone=zone, body=config).execute()

            # Wait for the operation to complete
            while not operation['status'] == 'DONE':
                operation = compute_client.zoneOperations().get(
                    project=project, zone=zone, operation=operation['name']).execute()

            # VM has been created successfully, return a simple HTTP response
            return render(request, 'create_vm_gcp_success.html', {'vm_name': vm_name})
        except Exception as e:
            # Log the error for debugging
            print(f"Error creating VM: {e}")

    return render(request, 'create_vm_gcp.html')


def list_vm_gcp(request):
    project_id = 'handliingvm'
    zone = 'us-central1-b'  # Replace 'us-central1-b' with your desired zone

    # Build paths inside the project like this: BASE_DIR / ...
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Add the path to your service account key file
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'

    # Load the service account key from the JSON file and create the credentials object
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)

    # Create a Compute Engine client
    compute_client = build('compute', 'v1', credentials=credentials)

    try:
        # Retrieve the list of VM instances in the specified zone
        vm_list = compute_client.instances().list(
            project=project_id, zone=zone).execute()

        # Extract VM names and IP addresses from the response
        vms = []
        if 'items' in vm_list:
            for vm in vm_list['items']:
                vm_name = vm['name']
                network_interfaces = vm.get('networkInterfaces', [])
                external_ip = network_interfaces[0]['accessConfigs'][0].get(
                    'natIP', '') if network_interfaces else None
                internal_ip = network_interfaces[0].get(
                    'networkIP', '') if network_interfaces else None
                vms.append(
                    {'name': vm_name, 'external_ip': external_ip or None, 'internal_ip': internal_ip or None})

        # Pass the list of VMs to the template
        return render(request, 'list_vm_gcp.html', {'vm_list': vms})
    except HttpError as e:
        # Log API errors for debugging
        print(f"Error listing VMs: {e}")
    except Exception as e:
        # Handle other potential exceptions here
        print(f"Unexpected error: {e}")

    # Return an empty list or an error template as needed
    return render(request, 'list_vm_gcp.html', {'vm_list': []})


def stop_vm_gcp(request):
    project_id = 'handliingvm'
    zone = 'us-central1-b'

    BASE_DIR = Path(__file__).resolve().parent.parent
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)
    compute_client = build('compute', 'v1', credentials=credentials)

    # Retrieve the list of VMs in the project
    vms = compute_client.instances().list(project=project_id, zone=zone).execute()
    vm_choices = [(vm['name'], vm['name']) for vm in vms.get('items', [])]

    class StopVMForm(forms.Form):
        selected_vm = forms.ChoiceField(
            label='Select VM to Stop', choices=vm_choices)

    if request.method == 'POST':
        form = StopVMForm(request.POST)
        if form.is_valid():
            selected_vm = form.cleaned_data['selected_vm']
            # Stop the selected VM
            operation = compute_client.instances().stop(
                project=project_id, zone=zone, instance=selected_vm).execute()
            while not operation['status'] == 'DONE':
                operation = compute_client.zoneOperations().get(project=project_id, zone=zone,
                                                                operation=operation['name']).execute()

            # Redirect to the confirmation page with VM details
            return redirect('vm_stopped', vm_name=selected_vm)
    else:
        form = StopVMForm()

    return render(request, 'stop_vm_gcp.html', {'form': form})


def vm_stopped(request, vm_name):
    return render(request, 'vm_stopped.html', {'vm_name': vm_name})


def delete_vm_gcp(request, vm_name):
    project_id = 'handliingvm'
    zone = 'us-central1-b'

    BASE_DIR = Path(__file__).resolve().parent.parent
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)
    compute_client = build('compute', 'v1', credentials=credentials)

    try:
        # Check if the VM exists before attempting to delete it
        vm = compute_client.instances().get(
            project=project_id, zone=zone, instance=vm_name).execute()
        # If the VM exists, delete it
        operation = compute_client.instances().delete(
            project=project_id, zone=zone, instance=vm_name).execute()
        while not operation['status'] == 'DONE':
            operation = compute_client.zoneOperations().get(project=project_id, zone=zone,
                                                            operation=operation['name']).execute()

        # Render the vm_deleted_gcp.html template after successful VM deletion
        return render(request, 'vm_deleted_gcp.html', {'vm_name': vm_name})
    except Exception as e:
        # Handle the case when the VM does not exist or other errors occur
        return HttpResponse(f'Error deleting VM: {e}')


async def create_machine_image_async(project_id, machine_image_name, selected_instance):
    # Add the path to your service account key file
    BASE_DIR = Path(__file__).resolve().parent.parent
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'

    # Load the service account key from the JSON file and create the credentials object
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)

    # Create a Compute Engine client
    compute_client = build('compute', 'v1', credentials=credentials)

    # Get the instance object using the instance name
    instance = compute_client.instances().get(
        project=project_id, zone='us-central1-b', instance=selected_instance).execute()

    # Create the machine image
    machine_image_body = {
        'name': machine_image_name,
        'sourceInstance': instance['selfLink']
    }

    operation = compute_client.machineImages().insert(
        project=project_id, body=machine_image_body).execute()

    # Wait for the operation to complete
    while not operation['status'] == 'DONE':
        operation = compute_client.globalOperations().get(
            project=project_id, operation=operation['name']).execute()

    return machine_image_name


async def create_machine_gcp(request):
    project_id = 'handliingvm'
    machine_image_name = ''  # Initialize the machine image name

    if request.method == 'POST':
        selected_instance = request.POST.get('selected_instance')
        machine_image_name = request.POST.get('machine_image_name')

        # Perform the machine image creation asynchronously
        asyncio.create_task(create_machine_image_async(
            project_id, machine_image_name, selected_instance))

        # Return an immediate response to the user
        return HttpResponse("Machine image creation initiated. Check back later for status.")

    # Rest of your GET request handling code (rendering the form)
    instance_choices = []
    compute_client = compute_v1.InstancesClient()
    instances = compute_client.list(
        project=project_id, zone='us-central1-b').items
    instance_choices = [instance.name for instance in instances]

    if request.GET.get('machine_image_name'):
        # If the 'machine_image_name' parameter is present in the GET request, it means the machine image creation is complete
        machine_image_name = request.GET.get('machine_image_name')
        return render(request, 'machine_image_created.html', {'machine_image_name': machine_image_name})

    return render(request, 'create_machine_gcp.html', {'instance_choices': instance_choices, 'machine_image_name': machine_image_name})


def list_machines_gcp(request):
    project_id = 'handliingvm'

    # Build paths inside the project like this: BASE_DIR / ...
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Add the path to your service account key file
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'

    # Load the service account key from the JSON file and create the credentials object
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)

    # Create a Compute Engine client
    compute_client = build('compute', 'v1', credentials=credentials)

    # List all machine images in the project
    machine_images = compute_client.machineImages().list(project=project_id).execute()

    # Extract relevant information from the machine images
    machine_image_list = []
    if 'items' in machine_images:
        for machine_image in machine_images['items']:
            machine_image_details = {
                'name': machine_image['name'],
                'sourceInstance': machine_image.get('sourceInstance', 'N/A'),
                'creationTimestamp': machine_image.get('creationTimestamp', 'N/A'),
            }
            machine_image_list.append(machine_image_details)

    context = {
        'machine_images': machine_image_list
    }

    return render(request, 'list_machine_images_gcp.html', context)


def delete_machine_image_gcp(request):
    project_id = 'handliingvm'  # Replace with your GCP project ID

    # Build paths inside the project like this: BASE_DIR / ...
    BASE_DIR = Path(__file__).resolve().parent.parent

    # Add the path to your service account key file
    SERVICE_ACCOUNT_KEY_FILE = BASE_DIR / 'hello' / 'handliingvm-13ecd6b93840.json'

    # Load the service account key from the JSON file and create the credentials object
    credentials = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_KEY_FILE)

    # Create a Compute Engine client
    compute_client = discovery.build('compute', 'v1', credentials=credentials)

    def get_machine_images():
        # List all machine images in the project
        machine_images = compute_client.machineImages().list(project=project_id).execute()

        # Extract relevant information from the machine images
        machine_image_list = []
        if 'items' in machine_images:
            for machine_image in machine_images['items']:
                machine_image_details = {
                    'name': machine_image['name'],
                    'sourceInstance': machine_image.get('sourceInstance', 'N/A'),
                    'creationTimestamp': machine_image.get('creationTimestamp', 'N/A'),
                }
                machine_image_list.append(machine_image_details)
        return machine_image_list

    if request.method == 'POST':
        selected_image = request.POST.get('selected_image', None)

        if selected_image:
            try:
                operation = compute_client.machineImages().delete(
                    project=project_id,
                    machineImage=selected_image
                ).execute()

                # Wait for the operation to complete (optional)
                # In practice, you might want to check the status of the operation and handle any errors accordingly.

                # Get the updated list of machine images after the deletion
                machine_image_list = get_machine_images()

                # Find the name of the deleted machine image for displaying the message
                deleted_machine_name = ""
                for machine_image in machine_image_list:
                    if machine_image['name'] == selected_image:
                        deleted_machine_name = machine_image['name']
                        break

                context = {
                    'deleted_machine_name': deleted_machine_name
                }

                return render(request, 'delete_machine_image_success.html', context)
            except Exception as e:
                return HttpResponse(f"Error deleting machine image {selected_image}: {str(e)}")

    # Get the initial list of machine images
    machine_image_list = get_machine_images()

    context = {
        'machine_images': machine_image_list
    }

    return render(request, 'delete_machine_image_gcp.html', context)


''''import boto3

def create_vm(request):
    aws_access_key_id = 'XXXXXXXXXXXXXXXXX'  # access key goes here
            # secret access key goes here
    aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    default_region = 'ap-south-1'

    if request.method == 'POST':
        # Get the VM name and other form data from the request
        vm_name = request.POST.get('vm_name')
        vm_type = request.POST.get('vm_type')
        region = request.POST.get('region', default_region)  # Use the default region if not provided in the request
        selected_ami = request.POST.get('selected_ami')  # Get the selected AMI

        try:
            # Create an EC2 resource using Boto3
            ec2 = boto3.resource('ec2', region_name=region, aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key)

            instance = ec2.create_instances(
                ImageId=selected_ami,  # Use the selected AMI
                InstanceType=vm_type,
                MinCount=1,
                MaxCount=1,
                KeyName='YOUR_EC2_KEY_PAIR_NAME',  # Replace with your EC2 key pair name
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': vm_name},
                        ]
                    }
                ]
            )

            # Wait for the instance to be running
            instance[0].wait_until_running()

            # Redirect to the list VMs page after creating the VM
            return redirect('list_vms')
        except Exception as e:
            # Handle the case where there is an error during instance creation
            return render(request, 'error.html', {'error_message': str(e)})

    # Fetch the list of AMIs
    ec2_client = boto3.client('ec2', region_name=default_region,
                              aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    response = ec2_client.describe_images(Owners=['self'])
    amis = response['Images']

    # Render the create VM form with the list of AMIs
    return render(request, 'create_vm.html', {'amis': amis})'''

def create_vm(request):
    aws_access_key_id = 'XXXXXXXXXXXXXXXXX'  # access key goes here
    aws_secret_access_key = 'XXXXXXXXXXXXXXXXX'
    default_region = 'ap-south-1'

    if request.method == 'POST':
        try:
            # Get the VM name and other form data from the request
            vm_name = request.POST.get('vm_name')
            vm_type = request.POST.get('vm_type')
            selected_ami = request.POST.get(
                'selected_ami')  # Get the selected AMI

            # Create an EC2 resource using Boto3
            ec2 = boto3.resource('ec2', region_name=default_region,
                                 aws_access_key_id=aws_access_key_id,
                                 aws_secret_access_key=aws_secret_access_key)

            instance = ec2.create_instances(
                ImageId=selected_ami,
                InstanceType=vm_type,
                MinCount=1,
                MaxCount=1,
                KeyName='XXXX',  # Replace with your EC2 key pair name
                TagSpecifications=[
                    {
                        'ResourceType': 'instance',
                        'Tags': [
                            {'Key': 'Name', 'Value': vm_name},
                        ]
                    }
                ]
            )

            # Wait for the instance to be running
            instance[0].wait_until_running()

            # Redirect to the list VMs page after creating the VM
            return redirect('list_vms')

        except Exception as e:
            # Handle any exceptions that occurred during VM creation
            return HttpResponse(f"An error occurred: {e}")

    # Fetch the list of AMIs
    ec2_client = boto3.client('ec2', region_name=default_region,
                              aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key)
    response = ec2_client.describe_images(Owners=['self'])
    amis = response['Images']

    # Render the create VM form with the list of AMIs
    return render(request, 'create_vm.html', {'amis': amis})


def list_vms(request):
    # Create a session using your AWS credentials
    session = boto3.Session(
        aws_access_key_id='XXXXXXXXXXXXXXXXx',  # Replace with your AWS access key
        # Replace with your AWS secret key
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXX',
        region_name='ap-south-1'  # Update with your desired AWS region
    )

    # Create an EC2 resource object
    ec2_resource = session.resource('ec2')

    # Retrieve all instances
    instances = ec2_resource.instances.all()

    # Prepare a list to store VM information
    vms = []

    # Iterate over the instances and collect VM details
    for instance in instances:
        vm = {
            'id': instance.id,
            'name': instance.tags[0]['Value'] if instance.tags else 'N/A',
            'type': instance.instance_type,
            'region': instance.placement['AvailabilityZone'],
            'public_ip': instance.public_ip_address,
            'instance_state': instance.state['Name'],  # Add the instance state
        }
        vms.append(vm)

    # Get the parameter for sorting (if provided by the user)
    sort_by = request.GET.get('sort_by', None)

    # Sort the VMs based on the selected column
    if sort_by:
        if sort_by == 'instance_state':
            vms.sort(key=lambda x: x[sort_by])
        else:
            vms.sort(key=lambda x: x[sort_by].lower())

    # Pass the VMs data and sort_by parameter to the template for rendering
    return render(request, 'list_vms.html', {'vms': vms, 'sort_by': sort_by})


def stop_vm(request):
    # Create a session using your AWS credentials
    session = boto3.Session(
        aws_access_key_id='XXXXXXXXXXXXXXXXXX',  # Replace with your AWS access key
        # Replace with your AWS secret key
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXX',
        region_name='ap-south-1'  # Update with your desired AWS region
    )

    # Create an EC2 resource object
    ec2_resource = session.resource('ec2')

    if request.method == 'POST':
        selected_vm_id = request.POST.get('selected_vm', None)

        if selected_vm_id:
            # Stop the selected VM
            instance = ec2_resource.Instance(selected_vm_id)
            instance.stop()

            # Get the VM name for the message
            vm_name = instance.tags[0]['Value'] if instance.tags else 'N/A'

            # Redirect to the confirmation page (vm_stopped2.html) with the VM name as a parameter
            return redirect('list_vms')

    # Retrieve all running instances
    instances = ec2_resource.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}])

    # Prepare a list of available VMs for the dropdown menu
    available_vms = [{'id': instance.id, 'name': instance.tags[0]['Value'] if instance.tags else instance.id}
                     for instance in instances]

    return render(request, 'stop_vm.html', {'available_vms': available_vms})


def delete_vm(request):
    # Create a session using your AWS credentials
    session = boto3.Session(
        aws_access_key_id='XXXXXXXXXXXXXXXXXXX',  # Replace with your AWS access key
        # Replace with your AWS secret key
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXXX',
        region_name='ap-south-1'  # Update with your desired AWS region
    )

    # Create an EC2 resource object
    ec2_resource = session.resource('ec2')

    # Retrieve all stopped instances
    instances = ec2_resource.instances.filter(
        Filters=[{'Name': 'instance-state-name', 'Values': ['stopped']}])

    # Prepare a list of stopped VMs for the dropdown menu
    stopped_vms = [{'id': instance.id, 'name': instance.tags[0]['Value'] if instance.tags else instance.id}
                   for instance in instances]

    if request.method == 'POST':
        selected_vm_id = request.POST.get('selected_vm', None)

        if selected_vm_id:
            # Terminate the selected VM
            instance = ec2_resource.Instance(selected_vm_id)
            instance.terminate()

            # Redirect to the list_vms function after deleting the VM
            return redirect(reverse('list_vms'))

    return render(request, 'delete_vm.html', {'stopped_vms': stopped_vms})


def is_instance_busy(instance_id):
    if instance_id.endswith("busy"):
        return True
    else:
        return False


def create_ami(request):
    # Set the AWS region to ap-south-1
    region_name = 'ap-south-1'

    if request.method == 'POST':
        # Retrieve the form data
        instance_id = request.POST['instance_id']
        ami_name = request.POST['ami_name']
        description = request.POST['description']

        # Check if the instance is busy
        if is_instance_busy(instance_id):
            return render(request, 'busyincreation.html')

        try:
            # Create the EC2 client with the specified region
            ec2_client = boto3.client(
                'ec2',
                region_name=region_name,
                # Replace with your AWS access key ID
                aws_access_key_id='XXXXXXXXXXXXXXXXXXX',
                # Replace with your AWS secret access key
                aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXX'
            )
            response = ec2_client.create_image(
                InstanceId=instance_id,
                Name=ami_name,
                Description=description
            )
            ami_id = response['ImageId']

            # Pass the AMI ID to the template for rendering
            context = {
                'ami_id': ami_id,
            }
            return render(request, 'ami_created.html', context)
        except Exception as e:
            error_message = f"Error: {str(e)}"
            context = {'error_message': error_message}
            return render(request, 'create_ami.html', context)

    # Retrieve the active instances for the dropdown
    ec2_client = boto3.client(
        'ec2',
        region_name=region_name,
        # Replace with your AWS access key ID
        aws_access_key_id='XXXXXXXXXXXXXXXX',
        # Replace with your AWS secret access key
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXXXXX'
    )
    response = ec2_client.describe_instances(
        Filters=[
            {
                'Name': 'instance-state-name',
                'Values': ['running']  # Retrieve only running instances
            }
        ]
    )
    active_instances = []
    for reservation in response['Reservations']:
        for instance in reservation['Instances']:
            active_instances.append({
                'instance_id': instance['InstanceId'],
            })

    return render(request, 'create_ami.html', {'active_instances': active_instances})


def list_amis(request):
    # Get the selected AWS region from the request
    region = request.GET.get('region')

    # Create a session using your AWS credentials
    session = boto3.Session(
        aws_access_key_id='XXXXXXXXXXXXXXXXXXXXXXX',  # access key goes here
        # secret access key goes here
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX',
        region_name='ap-south-1'  # Update with your desired AWS region
    )

    # Create an EC2 resource object
    ec2_resource = session.resource('ec2')

    # Retrieve self-created AMIs based on the selected region
    amis = ec2_resource.images.filter(Owners=['self'])

    # Prepare a list to store AMI information
    amis_data = []

    # Iterate over the AMIs and collect relevant details
    for ami in amis:
        ami_data = {
            'id': ami.id,
            'name': ami.name,
            'description': ami.description,
            'architecture': ami.architecture
        }
        amis_data.append(ami_data)

    # Pass the AMIs data and selected region to the template for rendering
    context = {
        'amis': amis_data,
    }

    return render(request, 'list_amis.html', context)


def delete_ami(request):
    # Create a session using your AWS credentials
    session = boto3.Session(
        aws_access_key_id='XXXXXXXXXXXXXXXX',  # Replace with your AWS access key
        # Replace with your AWS secret key
        aws_secret_access_key='XXXXXXXXXXXXXXXXXXXXXX',
        region_name='ap-south-1'  # Update with your desired AWS region
    )

    # Create an EC2 resource object
    ec2_resource = session.resource('ec2')

    # Retrieve all owned AMIs
    amis = ec2_resource.images.filter(Owners=['self'])

    # Prepare a list of owned AMIs for the dropdown menu
    owned_amis = [{'id': ami.id, 'name': ami.name} for ami in amis]

    if request.method == 'POST':
        selected_ami_id = request.POST.get('selected_ami', None)

        if selected_ami_id:
            # Deregister the selected AMI
            ami = ec2_resource.Image(selected_ami_id)
            ami.deregister()

            # Redirect to the list_amis function after deleting the AMI
            return redirect('list_amis')

    return render(request, 'delete_ami.html', {'owned_amis': owned_amis})
