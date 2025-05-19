/*-----------------------------------------------------------------
   Jenkinsfile – Release-notes pipeline (blank-diff version)
------------------------------------------------------------------*/
pipeline {
  agent any

  /* Disable Declarative’s automatic checkout */
  options { skipDefaultCheckout() }

  /* ------------ Secrets (Manage Jenkins → Credentials) ------------ */
  environment {
    GOOGLE_API_KEY = credentials('gcp-gemini-key')
    CONF_DOMAIN    = credentials('conf-domain')
    CONF_SPACE     = credentials('conf-space')
    CONF_USER      = credentials('conf-user')
    CONF_TOKEN     = credentials('conf-token')
    // GITHUB_TOKEN = credentials('gh-logs-pat')   // optional, if/when you add it
    SLEEP_SECONDS  = '5'
  }

  stages {

    /* 1) Clean checkout so we always get a fresh workspace */
    stage('Checkout') {
      steps {
        deleteDir()    // wipe any previous build leftovers
        checkout scm   // full Git clone of your repo
      }
    }

    /* 2) Build the Docker image */
    stage('Build Agent') {
      steps {
        sh '''
          # Drop Windows-only TLS vars; leave DOCKER_HOST pointing at the socket
          unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH

          docker build -t changelog-agent:latest -f docker/Dockerfile .
        '''
      }
    }

    /* 3) Run the changelog-agent container without a raw diff */
    stage('Generate Changelog') {
      steps {
        script {
          // Prepare output directory
          sh 'mkdir -p output'

          // Grab just the commit message (we’re omitting the diff for now)
          def msg = sh(script: 'git log -1 --pretty=%B', returnStdout: true).trim()

          // Run the container — note the blank COMMIT_DIFF so agent won’t error
          sh """
            unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH
            docker run --rm \
              -v ${WORKSPACE}/output:/app/output \
              -e GOOGLE_API_KEY='${GOOGLE_API_KEY}' \
              -e CONF_DOMAIN='${CONF_DOMAIN}' \
              -e CONF_SPACE='${CONF_SPACE}' \
              -e CONF_USER='${CONF_USER}' \
              -e CONF_TOKEN='${CONF_TOKEN}' \
              -e COMMIT_MSG='${msg}' \
              -e COMMIT_DIFF='' \
              changelog-agent:latest
          """
        }
        // Pause so you don’t hit Gemini’s rate limit
        sleep time: SLEEP_SECONDS.toInteger(), unit: 'SECONDS'
      }
    }

    /* 4) Optional: push the Markdown to your release-logs repo */
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
