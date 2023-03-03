import os
import json
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from ibm_schematics.schematics_v1 import SchematicsV1
import time 

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

def getWorkspaceOutputs(workspaceId, schematicsService):
    wsOutputs = schematicsService.get_workspace_outputs(
        w_id=workspaceId,
    ).get_result()

    print(json.dumps(wsOutputs, indent=2))

try:
    updateWorkspace(workspaceId, refreshToken, schematicsService)
    planWorkspace(workspaceId, refreshToken, schematicsService)
    applyWorkspace(workspaceId, refreshToken, schematicsService)
    getWorkspaceOutputs(workspaceId, schematicsService)
except ApiException as e:
     print("Workspace update failes with status code " + str(e.code) + ": " + e.message)
