# Stop on errors
$ErrorActionPreference = "Stop"

# Get the current subscription
$SubscriptionId = az account show --query id -o tsv

Write-Host "Using subscription: $SubscriptionId"

# Create the policy definition
az policy definition create --name require-rg-tags  --display-name "Require Resource Group Tags" --description  "Require mandatory tags and validate their values." --mode All --rules "require-tags-resource-groups.json"
  
# Assign the policy to the subscription
az policy assignment create --name require-rg-tags --display-name "Require Resource Group Tags" --policy require-rg-tags --scope "/subscriptions/$SubscriptionId"

Write-Host "Policy successfully created and assigned."

#
# Run smoke test, generate a new resource group, witout using tags
# this should fail
#
az group create --name myresourcegroup --location norwayeast