# GitHub Actions CI/CD - Quick Start Guide

## Files Created ✅
- `backend.tf` - S3 remote state configuration
- `.github/workflows/terraform-validate.yml` - Branch validation
- `.github/workflows/terraform-plan-pr.yml` - PR planning
- `.github/workflows/terraform-apply.yml` - Auto-apply on main
- `GITHUB_ACTIONS_SETUP.md` - Full implementation guide (11 KB)
- `IMPLEMENTATION_STATUS.md` - Summary of work done

## Do This Now (in order)

### 1. AWS Setup (local terminal) - 10 min
Copy-paste these commands to create S3, DynamoDB, and IAM user:

```bash
# Set variables
BUCKET="meraki-home-terraform-state"
TABLE="terraform-locks"
USER="github-actions-meraki"
REGION="us-east-1"

# 1. Create S3 bucket with encryption & versioning
aws s3api create-bucket --bucket $BUCKET --region $REGION
aws s3api put-bucket-versioning --bucket $BUCKET --versioning-configuration Status=Enabled
aws s3api put-bucket-encryption --bucket $BUCKET --server-side-encryption-configuration '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"AES256"}}]}'
aws s3api put-public-access-block --bucket $BUCKET --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# 2. Create DynamoDB lock table
aws dynamodb create-table --table-name $TABLE --attribute-definitions AttributeName=LockID,AttributeType=S --key-schema AttributeName=LockID,KeyType=HASH --billing-mode PAY_PER_REQUEST --region $REGION

# 3. Create IAM user for CI/CD
aws iam create-user --user-name $USER
KEYS=$(aws iam create-access-key --user-name $USER)
echo "==== COPY THESE VALUES ===="
echo $KEYS | jq -r '.AccessKey | "AWS_ACCESS_KEY_ID=\(.AccessKeyId)\nAWS_SECRET_ACCESS_KEY=\(.SecretAccessKey)"'
echo "============================"

# 4. Attach permissions to user
aws iam put-user-policy --user-name $USER --policy-name meraki-terraform --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {"Effect":"Allow","Action":["s3:ListBucket","s3:GetBucketVersioning"],"Resource":"arn:aws:s3:::meraki-home-terraform-state"},
    {"Effect":"Allow","Action":["s3:GetObject","s3:PutObject","s3:DeleteObject"],"Resource":"arn:aws:s3:::meraki-home-terraform-state/*"},
    {"Effect":"Allow","Action":["dynamodb:PutItem","dynamodb:GetItem","dynamodb:DeleteItem","dynamodb:DescribeTable"],"Resource":"arn:aws:dynamodb:us-east-1:*:table/terraform-locks"}
  ]
}'
```

**Save the AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY from output above!**

### 2. Migrate Local State to S3 (local terminal) - 5 min
```bash
cd /Users/lsudduth/Documents/src/meraki-home

# Set AWS credentials
export AWS_ACCESS_KEY_ID="paste-from-step-1"
export AWS_SECRET_ACCESS_KEY="paste-from-step-1"
export AWS_REGION="us-east-1"

# Migrate state (answer YES when prompted)
terraform init

# Verify it worked
terraform state list | wc -l  # Should show 135

# Delete local state files
rm terraform.tfstate terraform.tfstate.backup

# Verify remote state still works
terraform plan  # Should show "No changes"
```

### 3. Add GitHub Secrets - 5 min
Go to: **GitHub → Settings → Secrets and variables → Actions → New repository secret**

Add these 5 secrets:

| Name | Value |
|------|-------|
| `MERAKIAPIKEY` | Run: `echo $MERAKIAPIKEY` locally |
| `AWS_ACCESS_KEY_ID` | From step 1 output |
| `AWS_SECRET_ACCESS_KEY` | From step 1 output |
| `AWS_REGION` | `us-east-1` |
| `S3_BUCKET` | `meraki-home-terraform-state` |

Verify:
```bash
gh secret list --repo lsudduth/meraki-home
```

### 4. Commit & Push - 1 min
```bash
cd /Users/lsudduth/Documents/src/meraki-home

git add backend.tf .github/ GITHUB_ACTIONS_SETUP.md IMPLEMENTATION_STATUS.md

git commit -m "Add GitHub Actions CI/CD pipeline with S3 backend

- Configure S3 bucket for encrypted remote state management
- Add DynamoDB locking to prevent concurrent Terraform runs
- Create terraform-validate workflow for all branches
- Create terraform-plan-pr workflow for PR validation
- Create terraform-apply workflow for auto-apply on main branch"

git push origin main
```

### 5. Test Workflows - 15 min
```bash
# Create test branch
git checkout -b test/ci

# Make small change
echo "# Test" >> variables.tf

# Commit and push
git add variables.tf
git commit -m "Test: CI workflow"
git push origin test/ci

# Create PR
gh pr create --title "Test: CI/CD workflow" --body "Testing"

# Wait for workflows to run (GitHub Actions tab)
# Should see: terraform-validate ✅ and terraform-plan ✅

# Merge PR
gh pr merge --auto --squash

# Watch terraform-apply run on main
gh repo view --web  # Open Actions tab
```

Verify state updated:
```bash
aws s3api head-object --bucket meraki-home-terraform-state --key meraki-home/terraform.tfstate
# Should show recent LastModified timestamp
```

---

## How It Works

| Trigger | Workflow | What Happens |
|---------|----------|--------------|
| Push to any branch | `terraform-validate` | Format ✓ → Init ✓ → Validate ✓ |
| Open/update PR to main | `terraform-plan-pr` | Plan runs, posts comment to PR |
| Merge PR to main | `terraform-apply` | **Auto-applies** infrastructure changes |

---

## Troubleshooting

**S3 bucket already exists?**
```bash
# Use different name in backend.tf and try again
aws s3 ls | grep meraki
```

**Access Denied in workflow?**
- Double-check all 5 GitHub secrets are set correctly
- Verify IAM user policy attached in step 1

**State migration failed?**
```bash
# Restore local state from backup
mv terraform.tfstate.backup terraform.tfstate
terraform init  # Try again
```

**DynamoDB table already exists?**
```bash
aws dynamodb delete-table --table-name terraform-locks
# Wait 30 sec, then recreate
```

---

## Full Documentation

See **GITHUB_ACTIONS_SETUP.md** for:
- Complete AWS CLI commands with explanations
- GitHub UI step-by-step screenshots instructions
- All expected outputs for verification
- Comprehensive troubleshooting guide
- Security best practices
- Cost breakdown

---

## Status

✅ All code created and ready to commit
⏳ Awaiting AWS infrastructure setup (Phase 1)
⏳ Awaiting GitHub secrets configuration (Phase 3)

**Estimated time to completion:** 30-40 minutes from start

Next: Run the AWS setup commands above
