import boto3

iam = boto3.client("iam")

GROUPS = {
    "ConsoleFusione": [
        "mario.rossi",
        "anna.verdi",
    ],
    "BigliettoDigitale": [
        "luca.bianchi",
        "paolo.neri",
    ],
}

TEMP_PASSWORD = "TempPassword123!"


def delete_all_users():
    for user in iam.list_users()["Users"]:

        username = user["UserName"]

        print(f"Deleting user {username} ...")

        #
        # Remove user from all groups he/she belongs to
        #
        for group in iam.list_groups_for_user(UserName=username)["Groups"]:
            iam.remove_user_from_group(GroupName=group["GroupName"], UserName=username)

        try:
            iam.delete_login_profile(UserName=username)
        except:
            pass
        
        #
        # Remove any credentials and the the record within IAM
        #
        for key in iam.list_access_keys(UserName=username)["AccessKeyMetadata"]:
            iam.delete_access_key(UserName=username, AccessKeyId=key["AccessKeyId"])

        iam.delete_user(UserName=username)
        print(f"Deleting user {username} ... completed!")


def delete_all_groups():
    for group in iam.list_groups()["Groups"]:

        group_name = group["GroupName"]

        print(f"Deleting group {group_name} ...")

        #
        # Remove all existing policies from associated group
        #
        for policy in iam.list_attached_group_policies(GroupName=group_name)["AttachedPolicies"]:
            iam.detach_group_policy(GroupName=group_name, PolicyArn=policy["PolicyArn"])

        #
        # Delete group
        #
        iam.delete_group(GroupName=group_name)
        print(f"Deleting group {group_name} ... completed!")


def create_group(group_name):
    print(f"Creating group {group_name} ...")

    #
    # Create group an attach a policy
    #
    iam.create_group(GroupName=group_name)
    iam.attach_group_policy(GroupName=group_name, PolicyArn="arn:aws:iam::aws:policy/IAMUserChangePassword")

    print(f"Creating group {group_name} ... completed!")


def create_user(group_name, username):
    print(f"Creating user {username} ...")

    #
    # Create a user, a login and let the user membership
    # group
    #
    iam.create_user(UserName=username)
    iam.create_login_profile(UserName=username, Password=TEMP_PASSWORD, PasswordResetRequired=True,)
    iam.add_user_to_group(GroupName=group_name, UserName=username)

    print(f"Creating user {username} ... completed!")


def create_all_groups():
    for group_name, users in GROUPS.items():
        create_group(group_name)
        for username in users:
            create_user(group_name, username)

if __name__ == "__main__":
    delete_all_users()
    delete_all_groups()
    create_all_groups()