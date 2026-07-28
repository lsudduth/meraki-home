# GitHub Actions CI/CD Implementation Checklist

## Phase 1: AWS Infrastructure Setup (Execute Locally)

**⚠️ CRITICAL: Do these steps BEFORE committing to git**

### Prerequisites
- AWS CLI v2 configured with credentials that have IAM/S3/DynamoDB permissions
- Access to AWS Console (for verification)

### Step 1.1: Create S3 Bucket
```bash
# Set these variables for consistency
BUCKET_NAME="meraki-home-terraform-state"
REGION="us-east-1"

# Create bucket
aws s3api create-bucket \
  --bucket $BUCKET_NAME \
  --region $REGION

# Enable versioning (protect against accidental deletion)
aws s3api put-bucket-versioning \
  --bucket $BUCKET_NAME \
  --versioning-configuration Status=Enabled

# Enable encryption
aws s3api put-bucket-encryption \
  --bucket $BUCKET_NAME \
  --server-side-encryption-configuration '{
    "Rules": [{
      "ApplyServerSideEncryptionByDefault": {
        "SSEAlgorithm": "AES256"
      }
    }]
  }'

# Block public access
aws s3api put-public-access-block \
  --bucket $BUCKET_NAME \
  --public-access-block-configuration \
    "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"

# Verify
aws s3 ls s3://$BUCKET_NAME/
```

**Expected Output:** ✅ Empty bucket listing

### Step 1.2: Create DynamoDB Lock Table
```bash
TABLE_NAME="terraform-locks"
REGION="us-east-1"

aws dynamodb create-table \
  --table-name $TABLE_NAME \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST \
  --region $REGION

# Verify (wait 10 seconds for table to be created)
sleep 10
aws dynamodb describe-table --table-name $TABLE_NAME --region $REGION | jq '.Table.TableStatus'
```

**Expected Output:** ✅ `"ACTIVE"`

### Step 1.3: Create IAM User for CI/CD
```bash
USERNAME="github-actions-meraki"

# Create user
aws iam create-user --user-name $USERNAME

# Create access key (output includes AccessKeyId and SecretAccessKey)
KEYS=$(aws iam create-access-key --user-name $USERNAME)
ACCESS_KEY=$(echo $KEYS | jq -r '.AccessKey.AccessKeyId')
SECRET_KEY=$(echo $KEYS | jq -r '.AccessKey.SecretAccessKey')

echo "=== SAVE THESE VALUES ===" 
echo "AWS_ACCESS_KEY_ID=$ACCESS_KEY"
echo "AWS_SECRET_ACCESS_KEY=$SECRET_KEY"
echo "========================"

# Create and attach policy
aws iam put-user-policy --user-name $USERNAME \
  --policy-name meraki-terraform-policy \
  --policy-document '{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:ListBucket",
        "s3:GetBucketVersioning"
      ],
      "Resource": "arn:aws:s3:::meraki-home-terraform-state"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::meraki-home-terraform-state/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:DeleteItem",
        "dynamodb:DescribeTable"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:*:table/terraform-locks"
    }
  ]
}'
```

**Expected Output:** ✅ User created with access keys displayed

---

## Phase 2: Local State Migration (Execute Locally)

### Step 2.1: Prepare Environment
```bash
# Set AWS credentials from Step 1.3
export AWS_ACCESS_KEY_ID="<from Step 1.3>"
export AWS_SECRET_ACCESS_KEY="<from Step 1.3>"
export AWS_REGION="us-east-1"

# Verify S3 bucket access
aws s3 ls s3://meraki-home-terraform-state/
```

**Expected Output:** ✅ Empty (bucket is ready)

### Step 2.2: Migrate State to S3
```bash
cd /Users/lsudduth/Documents/src/meraki-home

# Run terraform init
# When prompted: "Do you want to copy existing state to the new backend?"
# Answer: YES
terraform init

# Verify state was uploaded
aws s3 ls s3://meraki-home-terraform-state/meraki-home/

# Verify state loads correctly
terraform state list | head -5

# Show local state files before deletion
ls -lh terraform.tfstate*
```

**Expected Output:** ✅ 
- S3 listing shows `terraform.tfstate`
- `terraform state list` shows resources (135 expected)
- Local `terraform.tfstate*` files exist as backup

### Step 2.3: Clean Up Local State (ONLY after verification)
```bash
# ⚠️ ONLY do this after confirming S3 state works!
rm -i terraform.tfstate terraform.tfstate.backup

# Verify remote state still works
terraform plan | head -20
```

**Expected Output:** ✅ No changes detected (state is in sync)

---

## Phase 3: GitHub Repository Setup

### Step 3.1: Add GitHub Secrets

**GitHub UI Path:** Settings → Secrets and variables → Actions → New repository secret

**Add these 5 secrets (exact names):**

| Secret Name | Value | Where to get it |
|------------|-------|-----------------|
| `MERAKIAPIKEY` | Your Meraki API key | `echo $MERAKIAPIKEY` locally |
| `AWS_ACCESS_KEY_ID` | From Step 1.3 output | AWS IAM console |
| `AWS_SECRET_ACCESS_KEY` | From Step 1.3 output | AWS IAM console (save it!) |
| `AWS_REGION` | `us-east-1` | Same as bucket region |
| `S3_BUCKET` | `meraki-home-terraform-state` | Bucket name from Step 1.1 |

**Verify secrets:**
```bash
gh secret list --repo lsudduth/meraki-home
```

**Expected Output:**
```
MERAKIAPIKEY            actions    
AWS_ACCESS_KEY_ID       actions    
AWS_SECRET_ACCESS_KEY   actions    
AWS_REGION              actions    
S3_BUCKET               actions    
```

### Step 3.2: Enable Branch Protection (Optional but Recommended)

**GitHub UI Path:** Settings → Branches → Add rule for `main`

- ✅ Require pull request reviews before merging (1+ approval)
- ✅ Dismiss stale pull request approvals when new commits are pushed
- ✅ Require status checks to pass: `validate` workflow

---

## Phase 4: Commit and Push Configuration

### Step 4.1: Stage Files
```bash
cd /Users/lsudduth/Documents/src/meraki-home

git add backend.tf .github/workflows/*.yml

# Verify staging
git status
```

**Expected Output:** ✅ Shows 4 new files (backend.tf + 3 workflows)

### Step 4.2: Create Commit
```bash
git commit -m "Add GitHub Actions CI/CD pipeline with S3 backend

- Configure S3 bucket for encrypted remote state management
- Add DynamoDB locking to prevent concurrent Terraform runs
- Create terraform-validate workflow for all branches
- Create terraform-plan-pr workflow for PR validation with plan comments
- Create terraform-apply workflow for auto-apply on main branch push
- Prepare for automated infrastructure deployment"
```

### Step 4.3: Push to GitHub
```bash
git push origin main
```

---

## Phase 5: Testing & Verification

### Test 1: Validation Workflow (All Branches)
```bash
# Create a test branch
git checkout -b test/ci-workflow

# Make a minor change (e.g., add comment to variables.tf)
echo "# Test commit for CI validation" >> variables.tf

git add variables.tf
git commit -m "Test: CI workflow validation"
git push origin test/ci-workflow
```

**Expected Result:** ✅ 
- GitHub Actions "Terraform Validate" runs automatically
- Workflow completes (format check → init → validate)
- All checks pass

**Check:** Settings → Actions → "Terraform Validate" workflow runs

### Test 2: PR Planning Workflow
```bash
# Create PR from test branch to main
gh pr create --title "Test: CI/CD workflow" --body "Testing terraform plan in PR"

# Monitor Actions tab
gh pr view --web
```

**Expected Result:** ✅
- "Terraform Plan" workflow runs
- Plan comment appears on PR within 2-3 minutes
- Plan shows 0 changes (no actual changes made)

**Check:** PR → Conversation tab → Plan comment visible

### Test 3: Auto-Apply on Main
```bash
# Merge PR
gh pr merge --auto --squash --delete-branch

# Monitor Actions tab
gh repo view --web
```

**Expected Result:** ✅
- "Terraform Apply" workflow runs on main
- Apply completes successfully
- Commit comment shows success with S3 state location

**Check:** 
```bash
# Verify state updated in S3
aws s3api head-object \
  --bucket meraki-home-terraform-state \
  --key meraki-home/terraform.tfstate

# Should show LastModified: <recent timestamp>
```

### Test 4: State Sync Verification
```bash
cd /Users/lsudduth/Documents/src/meraki-home

# Pull latest from GitHub (to get any changes)
git pull origin main

# Verify state loads from S3
terraform state list | wc -l
# Expected: 135 resources

# Run plan (should show no changes)
terraform plan | grep "No changes"
```

**Expected Output:** ✅
- `135` resources listed
- `No changes` message in plan

---

## Phase 6: Cleanup & Documentation

### Optional: Archive Old CI/CD Files
```bash
# If you have Jenkinsfile or .gitlab-ci.yml:
git rm Jenkinsfile .gitlab-ci.yml  # or move to .archive/ folder
git commit -m "Archive: Remove legacy CI/CD configuration

GitHub Actions is now the single source of truth for CI/CD."
```

### Document in README.md
```markdown
## CI/CD Pipeline

This project uses **GitHub Actions** for automated Terraform validation and deployment:

- **All Branches:** `terraform-validate.yml` - Format, init, validate checks
- **Pull Requests:** `terraform-plan-pr.yml` - Plan with PR comments
- **Main Branch:** `terraform-apply.yml` - Auto-apply infrastructure changes

### Secrets Required
- `MERAKIAPIKEY` - Cisco Meraki API key
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` - CI/CD IAM user credentials
- `AWS_REGION` - AWS region (us-east-1)
- `S3_BUCKET` - S3 bucket name for Terraform state

### State Management
- **Remote State:** S3 bucket `meraki-home-terraform-state`
- **State Locking:** DynamoDB table `terraform-locks`
- **Encryption:** AES256 at rest, TLS in transit

See [GitHub Actions Workflows](.github/workflows/) for implementation details.
```

---

## Troubleshooting

### Issue: "S3 bucket does not exist"
**Solution:** Verify bucket was created in Step 1.1
```bash
aws s3 ls | grep meraki-home-terraform-state
```

### Issue: "Access Denied" in workflows
**Solution:** Verify IAM user policy in Step 1.3
```bash
aws iam get-user-policy --user-name github-actions-meraki --policy-name meraki-terraform-policy
```

### Issue: State lock timeout (DynamoDB)
**Solution:** Clear stuck lock (be careful!)
```bash
aws dynamodb scan --table-name terraform-locks
aws dynamodb delete-item --table-name terraform-locks --key '{"LockID":{"S":"meraki-home/terraform.tfstate"}}'
```

### Issue: Workflow not triggering on push
**Solution:** Check workflow path filter in yaml (`paths:` section)
- Make sure you're modifying files that trigger the workflow
- Check GitHub Actions logs for why workflow skipped

### Issue: "terraform state list" shows fewer than 135 resources
**Solution:** State may not have migrated completely
```bash
terraform refresh  # Refresh from remote state
terraform state list | wc -l
```

---

## Cost Summary (AWS)

| Service | Estimated Monthly Cost |
|---------|------------------------|
| S3 Storage (state file) | $0.02 |
| S3 API Requests | $0.001 |
| DynamoDB (on-demand) | $0.25 |
| **Total** | **~$0.30** |

GitHub Actions: Free (unlimited for public/private repos)

---

## Next Steps

1. ✅ Execute Phase 1 (AWS infrastructure) - Do this first!
2. ✅ Execute Phase 2 (Local state migration) - Do before pushing to GitHub
3. ✅ Execute Phase 3 (GitHub secrets) - Required for workflows to run
4. ✅ Push code (Phase 4)
5. ✅ Test workflows (Phase 5)
6. ✅ Update documentation (Phase 6)

**Timeline:** ~30 minutes total (mostly waiting for AWS resources to provision)

**Status:** All workflow files created and committed. Awaiting manual AWS setup and GitHub secrets configuration.
