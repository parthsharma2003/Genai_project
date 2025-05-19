pipeline {
  /**********************************************************************
   * 1)  Where the pipeline runs
   * --------------------------------------------------------------------
   *    • Uses the host’s Docker daemon via /var/run/docker.sock
   *    • Works on a bare-metal controller OR an agent container
   *********************************************************************/
  agent {
    docker {
      image 'docker:24'                      // slim image that has the docker CLI
      args  '-v /var/run/docker.sock:/var/run/docker.sock'
    }
  }

  /**********************************************************************
   * 2)  Secrets – add these IDs under:  Manage Jenkins → Credentials
   *********************************************************************/
  environment {
    GOOGLE_API_KEY = credentials('gcp-gemini-key')
    CONF_DOMAIN    = credentials('conf-domain')
    CONF_SPACE     = credentials('conf-space')
    CONF_USER      = credentials('conf-user')
    CONF_TOKEN     = credentials('conf-token')
    GITHUB_TOKEN   = credentials('gh-logs-pat')   // optional, only used in Store Logs
    SLEEP_SECONDS  = '5'                          // API-rate-limit pause
  }

  stages {

    /****************  Checkout repo ****************/
    stage('Checkout') {
      steps { checkout scm }
    }

    /****************  Build Docker image ***********/
    stage('Build Agent') {
      steps {
        sh '''
          # -----------------------------------------------------------------
          # FIX: Host passes Windows-style Docker TLS vars into the container.
          # They break `docker build`.  Just drop them.
          # -----------------------------------------------------------------
          unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH

          docker build -t changelog-agent:latest -f docker/Dockerfile .
        '''
      }
    }

    /****************  Run the agent & publish page ***********/
    stage('Generate Changelog') {
      steps {
        script {
          // create a local dir that we mount into the container for artifacts
          sh 'mkdir -p output'

          // get commit message & diff for Gemini prompt
          def msg  = sh(script: 'git log -1 --pretty=%B',  returnStdout: true).trim()
          def diff = sh(script: 'git diff HEAD~1 HEAD',    returnStdout: true).trim()

          // run the agent
          sh """
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
        // small delay between calls to stay well under rate limits
        sleep time: SLEEP_SECONDS.toInteger(), unit: 'SECONDS'
      }
    }

    /****************  (Optional) push changelog .md to a logs repo ***********/
    stage('Store Logs to GitHub') {
      when { expression { env.GITHUB_TOKEN?.trim() } }   // run only if PAT is present
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

  /****************  Always run: archive raw diff, print banner ***********/
  post {
    always {
      archiveArtifacts artifacts: 'release.diff', fingerprint: true, allowEmptyArchive: true
      echo 'Pipeline complete.'
    }
  }
}
