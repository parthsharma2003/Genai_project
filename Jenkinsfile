/*-----------------------------------------------------------------
   Jenkinsfile  –  Release-notes pipeline
------------------------------------------------------------------*/

pipeline {
  /*--------------------------------------------------------------
   * 1)  Where the pipeline runs
   *-------------------------------------------------------------*/
  agent any        // runs on the Jenkins controller (or any free agent)

  /*--------------------------------------------------------------
   * 2)  Secrets from  Manage Jenkins → Credentials
   *-------------------------------------------------------------*/
  environment {
    GOOGLE_API_KEY = credentials('gcp-gemini-key')
    CONF_DOMAIN    = credentials('conf-domain')
    CONF_SPACE     = credentials('conf-space')
    CONF_USER      = credentials('conf-user')
    CONF_TOKEN     = credentials('conf-token')

    // GITHUB_TOKEN = credentials('gh-logs-pat')   // add later if you want Store Logs
    SLEEP_SECONDS  = '5'                           // pause between Gemini calls
  }

  /*--------------------------------------------------------------
   * 3)  Pipeline stages
   *-------------------------------------------------------------*/
  stages {

    /*------------------------  Checkout  -----------------------*/
    stage('Checkout') {
      steps { checkout scm }
    }

    /*----------------------  Build image  ----------------------*/
    stage('Build Agent') {
      steps {
        sh '''
          # Drop Windows-specific Docker TLS vars; keep DOCKER_HOST
          unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH

          docker build -t changelog-agent:latest -f docker/Dockerfile .
        '''
      }
    }

    /*-------------------  Generate changelog  ------------------*/
    stage('Generate Changelog') {
      steps {
        script {
          sh 'mkdir -p output'          // host dir for agent artefacts

          def msg  = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()
          def diff = sh(script: 'git diff HEAD~1 HEAD',   returnStdout: true).trim()

          sh """
            unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH      # keep DOCKER_HOST
            docker run --rm \
              -v ${WORKSPACE}/output:/app/output \
              -e GOOGLE_API_KEY='${GOOGLE_API_KEY}' \
              -e CONF_DOMAIN='${CONF_DOMAIN}' \
              -e CONF_SPACE='${CONF_SPACE}' \
              -e CONF_USER='${CONF_USER}' \
              -e CONF_TOKEN='${CONF_TOKEN}' \
              -e COMMIT_MSG='${msg}' \
              -e COMMIT_DIFF='${diff}' \
              changelog-agent:latest
          """
        }
        sleep time: SLEEP_SECONDS.toInteger(), unit: 'SECONDS'
      }
    }

    /*--------------  (optional) push logs repo  ----------------*/
    stage('Store Logs to GitHub') {
      when { expression { env.GITHUB_TOKEN?.trim() } }   // will be skipped until you add the PAT
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

  /*-----------------------  Post actions  ----------------------*/
  post {
    always {
      archiveArtifacts artifacts: 'release.diff',
                       fingerprint: true,
                       allowEmptyArchive: true
      echo 'Pipeline complete.'
    }
  }
}
