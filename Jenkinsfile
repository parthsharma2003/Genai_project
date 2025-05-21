pipeline {
  agent any
  options { skipDefaultCheckout() }

  environment {
    DOCKER_IMAGE = 'changelog-agent:latest'
    OUTPUT_DIR   = "${WORKSPACE}/output"
    LOG_DIR      = "${WORKSPACE}/logs"
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
          docker build -t ${DOCKER_IMAGE} -f docker/Dockerfile .
        '''
      }
    }

    stage('Generate Changelog') {
      environment {
        // credentials *are* allowed here
        GOOGLE_API_KEY = credentials('gcp-gemini-key')
        CONF_DOMAIN    = credentials('conf-domain')
        CONF_SPACE     = credentials('conf-space')
        CONF_USER      = credentials('conf-user')
        CONF_TOKEN     = credentials('conf-token')
        PROJECT_NAME   = 'GenAI Project'
        CHANGELOG_FORMAT = 'detailed'
      }
      steps {
        // Gather all of your git metadata *inside* steps:
        script {
          env.COMMIT_MSG    = sh(script: 'git log -1 --pretty=%B',          returnStdout: true).trim()
          env.COMMIT_HASH   = sh(script: 'git rev-parse HEAD',               returnStdout: true).trim()
          env.COMMIT_AUTHOR = sh(script: 'git log -1 --pretty=%an',          returnStdout: true).trim()
          // write diff to a file, then load into an env var
          sh 'git diff HEAD^ HEAD > release.diff || true'
          env.COMMIT_DIFF = readFile('release.diff').trim()
        }

        // Run the container, mounting two separate dirs for clarity:
        sh """
          mkdir -p ${OUTPUT_DIR} ${LOG_DIR}
          unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH
          docker run --rm \\
            -v ${OUTPUT_DIR}:/app/output \\
            -v ${LOG_DIR}:/app/logs \\
            -e GOOGLE_API_KEY=\"${GOOGLE_API_KEY}\" \\
            -e CONF_DOMAIN=\"${CONF_DOMAIN}\" \\
            -e CONF_SPACE=\"${CONF_SPACE}\" \\
            -e CONF_USER=\"${CONF_USER}\" \\
            -e CONF_TOKEN=\"${CONF_TOKEN}\" \\
            -e COMMIT_MSG=\"${COMMIT_MSG}\" \\
            -e COMMIT_DIFF=\"${COMMIT_DIFF}\" \\
            -e COMMIT_HASH=\"${COMMIT_HASH}\" \\
            -e COMMIT_AUTHOR=\"${COMMIT_AUTHOR}\" \\
            -e PROJECT_NAME=\"${PROJECT_NAME}\" \\
            -e CHANGELOG_FORMAT=\"${CHANGELOG_FORMAT}\" \\
            ${DOCKER_IMAGE}
        """
      }
    }

    stage('Store Logs to GitHub') {
      environment {
        // you can reference the same credential twice if you like:
        GIT_CREDENTIALS = credentials('gh-logs-pat')
      }
      steps {
        withCredentials([usernamePassword(
          credentialsId: 'gh-logs-pat',
          usernameVariable: 'GIT_USERNAME',
          passwordVariable: 'GIT_PASSWORD'
        )]) {
          sh """
            git config user.email "jenkins@ci.com"
            git config user.name  "Jenkins CI"
            mkdir -p logs
            cp ${LOG_DIR}/changelog_generator.log logs/changelog_generator_${BUILD_NUMBER}.log || true
            cp ${OUTPUT_DIR}/changelog.md logs/changelog_${GIT_COMMIT}.md || true
            git add logs/*
            git commit -m "Add changelog + log for build ${BUILD_NUMBER} (${GIT_COMMIT})" || true
            git push https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/parthsharma2003/Genai_project.git main
          """
        }
      }
    }
  }

  post {
    always {
      archiveArtifacts artifacts: 'output/**, release.diff, logs/**', fingerprint: true, allowEmptyArchive: true
      echo 'Pipeline complete.'
    }
    failure {
      echo 'Pipeline failed. Check archived logs in logs/changelog_generator.log for details.'
    }
  }
}
