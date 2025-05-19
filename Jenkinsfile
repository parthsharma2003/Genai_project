/*-----------------------------------------------------------------
   Jenkinsfile – Release-notes pipeline (COMMIT_DIFF hack)
------------------------------------------------------------------*/
pipeline {
  agent any

  /* Disable Declarative’s implicit checkout */
  options { skipDefaultCheckout() }

  environment {
    GOOGLE_API_KEY = credentials('gcp-gemini-key')
    CONF_DOMAIN    = credentials('conf-domain')
    CONF_SPACE     = credentials('conf-space')
    CONF_USER      = credentials('conf-user')
    CONF_TOKEN     = credentials('conf-token')
    // GITHUB_TOKEN = credentials('gh-logs-pat')   // optional later
    SLEEP_SECONDS  = '5'
  }

  stages {
    stage('Checkout') {
      steps {
        deleteDir()
        checkout scm
      }
    }

    stage('Build Agent') {
      steps {
        sh '''
          unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH
          docker build -t changelog-agent:latest -f docker/Dockerfile .
        '''
      }
    }

    stage('Generate Changelog') {
      steps {
        script {
          sh 'mkdir -p output'
          def msg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()

          sh """
            unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH
            docker run --rm \\
              -v ${WORKSPACE}/output:/app/output \\
              -e GOOGLE_API_KEY='${GOOGLE_API_KEY}' \\
              -e CONF_DOMAIN='${CONF_DOMAIN}' \\
              -e CONF_SPACE='${CONF_SPACE}' \\
              -e CONF_USER='${CONF_USER}' \\
              -e CONF_TOKEN='${CONF_TOKEN}' \\
              -e COMMIT_MSG='${msg}' \\
              -e COMMIT_DIFF=' ' \\
              changelog-agent:latest
          """
        }
        sleep time: SLEEP_SECONDS.toInteger(), unit: 'SECONDS'
      }
    }

    stage('Store Logs to GitHub') {
      when { expression { env.GITHUB_TOKEN?.trim() } }
      steps {
        script {
          def changelog = readFile("${WORKSPACE}/output/changelog.md")
          dir('release-logs') {
            git url: 'https://github.com/your-org/release-logs.git',
                credentialsId: 'gh-logs-pat'
            writeFile file: "${env.GIT_COMMIT}.md", text: changelog
            sh '''
              git add *.md
              git commit -m "Add changelog for ${GIT_COMMIT}" || echo "Nothing to commit"
              git push
            '''
          }
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'release.diff',
                       fingerprint: true,
                       allowEmptyArchive: true
      echo 'Pipeline complete.'
    }
  }
}
