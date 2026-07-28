pipeline {
    agent {
        docker {
            image 'danischm/nac:0.1.6'
            label 'digidev'
        }
    }

    environment {
        MERAKI_API_KEY = credentials('MERAKI_API_KEY')
        WEBEX_TOKEN = credentials('WEBEX_TOKEN')
        WEBEX_ROOM_ID = 'Y2lzY29zcGFyazovL3VzL1JPT00vNTFmMGNmODAtYjI0My0xMWU5LTljZjUtNWY0NGQ2ZTlmYWY0'
        GITHUB_TOKEN = credentials('GITHUB_TOKEN')
        REPO = env.GIT_URL.replaceFirst(/^.*?(?::\/\/.*?\/|:)(.*).git$/, '$1')
        GIT_COMMIT_MESSAGE = "${sh(returnStdout: true, script: 'git log -1 --pretty=%B ${GIT_COMMIT}').trim()}"
        GIT_COMMIT_AUTHOR = "${sh(returnStdout: true, script: 'git show -s --pretty=%an').trim()}"
        GIT_EVENT = "${(env.CHANGE_ID != null) ? 'Pull Request' : 'Push'}"
        domain = 'EMEA'
        org = 'nac-meraki-terraform'
        org_admin = 'netascode-admin'
        org_admin_email = 'meraki-adminn@netascode.cisco.com'
        network_name = 'nac-meraki-network-01'
        snmp_password = "TryH4rd3r!2026"
        network_password = "Bu1ldMore!2026"
        wireless_guest_psk = "GuestSecurePassword!2026"
        radius_accounting_secret = "Cisco123!2026"
        radius_secret = "Cisco123!2026"

    }

    options {
        disableConcurrentBuilds()
    }

    stages {
        stage('Setup') {
            steps {
                sh 'terraform init -input=false --upgrade'
            }
        }
        stage('Validate') {
            steps {
                sh "echo ${env.CHANGE_ID}"
                sh 'set -o pipefail && terraform fmt -check |& tee fmt_output.txt'
                sh 'set -o pipefail && nac-validate data/ -v DEBUG |& tee validate_output.txt'
            }
        }
        stage('Plan') {
            steps {
                sh 'terraform plan -out=plan.tfplan -input=false'
                sh 'terraform show -no-color plan.tfplan > plan.txt'
                sh 'terraform show -json plan.tfplan > plan.json'
                // sh 'python3 .ci/github-comment.py'
                archiveArtifacts 'plan.*'
            }
        }
        stage('Deploy') {
            when {
                branch 'master'
            }
            steps {
                sh 'terraform apply -input=false -auto-approve plan.tfplan'
            }
        }
        stage('Test') {
            when {
                branch 'master'
            }
            parallel {
                stage('Test Idempotency') {
                    steps {
                        sh 'terraform plan -input=false -detailed-exitcode'
                    }
                }
                stage('Test Integration') {
                    steps {
                        sh 'set -o pipefail && nac-test -d ./data -d ./defaults.yaml -t ./tests/templates -o ./tests/results |& tee test_output.txt'
                    }
                    post {
                        always {
                            archiveArtifacts 'tests/results/log.html, tests/results/output.xml, tests/results/report.html, tests/results/xunit.xml'
                            junit 'tests/results/xunit.xml'
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            sh "BUILD_STATUS=${currentBuild.currentResult} python3 .ci/webex-notification-jenkins.py"
            sh 'rm -rf plan.* *.txt tests/results'
        }
    }
}

