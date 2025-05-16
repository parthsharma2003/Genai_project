pipeline {
  agent any
  environment {
    GOOGLE_API_KEY = credentials('gcp-gemini-key')
    CONF_DOMAIN    = credentials('conf-domain')
    CONF_SPACE     = credentials('conf-space')
    CONF_USER      = credentials('conf-user')
    CONF_TOKEN     = credentials('conf-token')
    GITHUB_TOKEN   = credentials('gh-logs-pat')    // optional, for Store Logs stage
    SLEEP_SECONDS  = '5'                          // pause 5s between runs (≈12/min)
  }
  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Build Agent') {
      steps {
        // Adjust path to your Dockerfile if needed
        sh 'docker build -t changelog-agent:latest -f docker/Dockerfile .'
      }
    }

    stage('Generate Changelog') {
      steps {
        script {
          // Create output directory for volume mount
          sh 'mkdir -p output'

          // Grab the latest commit message & diff
          def msg  = sh(script: "git log -1 --pretty=%B", returnStdout: true).trim()
          def diff = sh(script: "git diff HEAD~1 HEAD",   returnStdout: true).trim()

          // Run the changelog-agent with volume mount
          sh """
            docker run --rm \
              -v ${WORKSPACE}/output:/app/output \
              -e GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
              -e CONF_DOMAIN="${CONF_DOMAIN}" \
              -e CONF_SPACE="${CONF_SPACE}" \
              -e CONF_USER="${CONF_USER}" \
              -e CONF_TOKEN="${CONF_TOKEN}" \
              -e COMMIT_MSG="${msg}" \
              -e COMMIT_DIFF="${diff}" \
              changelog-agent:latest
          """
        }
        // Throttle to avoid 429s
        sleep time: SLEEP_SECONDS.toInteger(), unit: 'SECONDS'
      }
    }

    stage('Store Logs to GitHub') {
      when { expression { env.GITHUB_TOKEN } }
      steps {
        script {
          // Read the Markdown changelog from the mounted volume
          def changelog = readFile("${WORKSPACE}/output/changelog.md")
          dir('release-logs') {
            git url: "https://github.com/your-org/release-logs.git",
                credentialsId: 'gh-logs-pat'
            writeFile file: "${env.GIT_COMMIT}.md", text: changelog
            sh '''
              git add *.md
              git commit -m "Add changelog for ${GIT_COMMIT}"
              git push
            '''
          }
        }
      }
    }
  }

  post {
    always {
      // Archive the raw diff for auditing (assuming it's generated elsewhere)
      archiveArtifacts artifacts: 'release.diff', fingerprint: true, allowEmptyArchive: true
      echo "Pipeline complete."
    }
  }
}