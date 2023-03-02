import os
import sys
import json
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
from ibm_cloud_sdk_core import ApiException
from ibm_schematics.schematics_v1 import SchematicsV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import time 

# Fetch the workspace ID and refresh token from environment variables
workspaceId = os.environ.get('WORKSPACE_ID')

# Set up IAM authenticator
authenticator = IAMAuthenticator(
    apikey=os.environ.get('IBMCLOUD_API_KEY'),
    client_id='bx',
    client_secret='bx'
    )

refreshToken = authenticator.token_manager.request_token()['refresh_token']

# Set up Schematics service client and endpoint 

schematics_service = SchematicsV1(authenticator=authenticator)
schematicsURL = "https://us.schematics.cloud.ibm.com"
schematics_service.set_service_url(schematicsURL)

# Construct the terraform taint command model
terraform_command_model = {
  'command': 'taint',
  'command_params': 'random_integer.location',
  'command_name': 'location-taint',
  'command_desc': 'Run taint on location resource',
}

print("Tainting location resource in Workspace.")

workspaceUpdate = schematics_service.run_workspace_commands(
    w_id=workspaceId,
    refresh_token=refreshToken,
    commands=[terraform_command_model],
    operation_name='taint-location',
    description='taint-location'
).get_result()

updateActivityId = workspaceUpdate.get('activityid')

while True:
    jobStatus = schematics_service.get_job(job_id=updateActivityId).get_result()['status']['workspace_job_status']['status_code']
    if (jobStatus == 'job_in_progress' or jobStatus == 'job_pending'):
        print("Workspace update in progress. Checking again in 20 seconds...")
        time.sleep(20)
    else:
        print("Workspace update complete. Starting Workspace plan.")
        break

workspacePlan = schematics_service.plan_workspace_command(
    w_id=workspaceId,
    refresh_token=refreshToken,
).get_result()

planActivityId = workspacePlan.get('activityid')

while True:
    planStatus = schematics_service.get_job(job_id=planActivityId).get_result()['status']['workspace_job_status']['status_code']
    if (planStatus == 'job_in_progress' or planStatus == 'job_pending'):
        print("Workspace plan in progress. Checking again in 20 seconds...")
        time.sleep(20)
    elif (planStatus == 'job_cancelled' or planStatus == 'job_failed'):
        print("Workspace plan failed. Please check the logs by running the following command: ibmcloud schematics job logs --id " + planActivityId)
        break
    else:
        print("Workspace plan complete. Starting Workspace apply.")
        break

workspaceApply = schematics_service.apply_workspace_command(
    w_id=workspaceId,
    refresh_token=refreshToken,
).get_result()

applyActivityId = workspaceApply.get('activityid')

while True:
    applyStatus = schematics_service.get_job(job_id=applyActivityId).get_result()['status']['workspace_job_status']['status_code']
    if (applyStatus == 'job_in_progress' or applyStatus == 'job_pending'):
        print("Workspace apply in progress. Checking again in 1 minute...")
        time.sleep(60)
    elif (applyStatus == 'job_cancelled' or applyStatus == 'job_failed'):
        print("Workspace apply failed. Please check the logs by running the following command: ibmcloud schematics job logs --id " + applyActivityId)
        break
    else:
        print("Workspace apply complete. Gathering workspace outputs.")
        break

workspaceOutputs = schematics_service.get_workspace_outputs(
    w_id=workspaceId,
).get_result()[0]['output_values']

print(workspaceOutputs)