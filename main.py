import os
import sys
import json
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from ibm_schematics.schematics_v1 import SchematicsV1
import time 
import base64
import etcd3

# Set up IAM authenticator and Refresh Token
authenticator = IAMAuthenticator(
    apikey=os.environ.get('IBMCLOUD_API_KEY'),
    client_id='bx',
    client_secret='bx'
    )

refreshToken = authenticator.token_manager.request_token()['refresh_token']

# Set up Schematics service client, endpoint, and workspace ID 
schematicsService = SchematicsV1(authenticator=authenticator)
schematicsURL = "https://us.schematics.cloud.ibm.com"
schematicsService.set_service_url(schematicsURL)
workspaceId = os.environ.get('WORKSPACE_ID')

etcdServiceVar = os.environ.get('DATABASES_FOR_ETCD_CONNECTION')
json_object = json.loads(etcdServiceVar)
connectionVars = list(json_object.values())[1]

certDetails = connectionVars['certificate']['certificate_base64']
ca_cert=base64.b64decode(certDetails)
decodedCert = ca_cert.decode('utf-8')

etcdCert = '/etc/ssl/certs/db-ca.crt'
with open(etcdCert, 'w+') as output_file:
    output_file.write(decodedCert)

etcdHost = connectionVars['hosts'][0]['hostname']
etcdPort = connectionVars['hosts'][0]['port']
etcdUser = connectionVars['authentication']['username']
etcdPass = connectionVars['authentication']['password']

etcdClient = etcd3.client(
    host=etcdHost, 
    port=etcdPort, 
    ca_cert=etcdCert,
    timeout=10, 
    user=etcdUser, 
    password=etcdPass
)

# define functions
def updateWorkspace(workspaceId, refreshToken, schematicsService):
    # Construct the terraform taint command model
    terraform_command_model = {
        'command': 'taint',
        'command_params': 'random_integer.location',
        'command_name': 'location-taint',
        'command_desc': 'Run taint on location resource',
    }

    print("Tainting location resource in Workspace.")

    wsUpdate = schematicsService.run_workspace_commands(
        w_id=workspaceId,
        refresh_token=refreshToken,
        commands=[terraform_command_model],
        operation_name='taint-location',
        description='taint-location'
    ).get_result()

    updateActivityId = wsUpdate.get('activityid')

    while True:
        jobStatus = schematicsService.get_job(job_id=updateActivityId).get_result()['status']['workspace_job_status']['status_code']
        if (jobStatus == 'job_in_progress' or jobStatus == 'job_pending'):
            print("Workspace update in progress. Checking again in 30 seconds...")
            time.sleep(30)
        elif (jobStatus == 'job_cancelled' or jobStatus == 'job_failed'):
            log.warning("Workspace update failed. Please check the logs by running the following command: ibmcloud schematics job logs --id " + updateActivityId)
            print("Workspace update failed. Please check the logs by running the following command: ibmcloud schematics job logs --id " + updateActivityId)
            break
        else:
            print("Workspace update complete. Proceeding to Workspace plan.")
            break

def planWorkspace(workspaceId, refreshToken, schematicsService):
    
    wsPlan = schematicsService.plan_workspace_command(
        w_id=workspaceId,
        refresh_token=refreshToken,
    ).get_result()

    planActivityId = wsPlan.get('activityid')

    while True:
        planStatus = schematicsService.get_job(job_id=planActivityId).get_result()['status']['workspace_job_status']['status_code']
        if (planStatus == 'job_in_progress' or planStatus == 'job_pending'):
            print("Workspace plan in progress. Checking again in 30 seconds...")
            time.sleep(30)
        elif (planStatus == 'job_cancelled' or planStatus == 'job_failed'):
            print("Workspace plan failed. Please check the logs by running the following command: ibmcloud schematics job logs --id " + planActivityId)
            break
        else:
            print("Workspace plan complete. Proceeding to Workspace apply.")
            break


def applyWorkspace(workspaceId, refreshToken, schematicsService):
    wsApply = schematicsService.apply_workspace_command(
        w_id=workspaceId,
        refresh_token=refreshToken,
    ).get_result()

    applyActivityId = wsApply.get('activityid')

    while True:
        applyStatus = schematicsService.get_job(job_id=applyActivityId).get_result()['status']['workspace_job_status']['status_code']
        if (applyStatus == 'job_in_progress' or applyStatus == 'job_pending'):
            print("Workspace apply in progress. Checking again in 1 minute...")
            time.sleep(60)
        elif (applyStatus == 'job_cancelled' or applyStatus == 'job_failed'):
            print("Workspace apply failed. Please check the logs by running the following command: ibmcloud schematics job logs --id " + applyActivityId)
            break
        else:
            print("Workspace apply complete. Gathering workspace outputs.")
            break

# Function to pull specific output value from Schematics workspace based on `instance` parameter
def getWorkspaceOutputs(schematicsService, workspaceId, instance):
    wsOutputs = schematicsService.get_workspace_outputs(
        w_id=workspaceId,
    ).get_result()

    outputValue = str(wsOutputs[0]['output_values'][0][instance]['value'])
    return outputValue

# Pull instance IDs from Schematics workspace
def pullOutput(instance):
    instanceId = getWorkspaceOutputs(schematicsService, workspaceId, instance=instance)
    return instanceId

def writeKeys(etcdClient):
    print("Connected to etcd service")
    print("attempting to write to etcd service")
    ubuntuInstanceID = str(pullOutput(instance = 'ubuntu_instance_id'))
    rockyInstanceID = str(pullOutput(instance = 'rocky_instance_id'))
    windowsInstanceID = str(pullOutput(instance = 'windows_instance_id'))
    storeUbuntuId = etcdClient.put('/current_servers/ubuntu/id', ubuntuInstanceID)
    storeRockyId = etcdClient.put('/current_servers/rocky/id', rockyInstanceID)
    storeWindowsId = etcdClient.put('/current_servers/windows/id', windowsInstanceID)
    print("Successfully wrote all instance ids to etcd service")
try:
    updateWorkspace(workspaceId, refreshToken, schematicsService)
    planWorkspace(workspaceId, refreshToken, schematicsService)
    applyWorkspace(workspaceId, refreshToken, schematicsService)
    writeKeys(etcdClient)
except ApiException as e:
     print("Workspace update failes with status code " + str(e.code) + ": " + e.message)
