pipeline {
  agent any
  options { skipDefaultCheckout() }

  environment {
    DOCKER_IMAGE   = 'changelog-agent:latest'
    OUTPUT_DIR     = "${WORKSPACE}/output"
    LOG_DIR        = "${WORKSPACE}/logs"

    // only credentials or literals here
    GOOGLE_API_KEY = credentials('gcp-gemini-key')
    CONF_DOMAIN    = credentials('conf-domain')
    CONF_SPACE     = credentials('conf-space')
    CONF_USER      = credentials('conf-user')
    CONF_TOKEN     = credentials('conf-token')

    PROJECT_NAME      = 'GenAI Project'
    CHANGELOG_FORMAT  = 'detailed'
    STAGE_NAME        = 'Generate Changelog'
    // JOB_NAME is already in env.JOB_NAME
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
      steps {
        script {
          // 1) Capture all Git metadata with shell
          env.COMMIT_MSG    = sh(script: 'git log -1 --pretty=%B',          returnStdout: true).trim()
          env.COMMIT_HASH   = sh(script: 'git rev-parse HEAD',               returnStdout: true).trim()
          env.COMMIT_AUTHOR = sh(script: 'git log -1 --pretty=%an',          returnStdout: true).trim()
          env.VERSION       = sh(script: 'git describe --tags --always --dirty || echo "Unknown"', returnStdout: true).trim()
          
          // 2) Save diff to file, then read it
          sh 'git diff HEAD^ HEAD > release.diff || true'
          env.COMMIT_DIFF = readFile('release.diff').trim() ?: 'No diff available'

          // 3) Make sure output & log dirs exist
          sh "mkdir -p ${OUTPUT_DIR} ${LOG_DIR}"
        }

        // 4) Run the container in one block
        sh '''
          unset DOCKER_TLS_VERIFY DOCKER_CERT_PATH
          docker run --rm \
            -v ${OUTPUT_DIR}:/app/output \
            -v ${LOG_DIR}:/app/logs \
            -e GOOGLE_API_KEY="${GOOGLE_API_KEY}" \
            -e CONF_DOMAIN="${CONF_DOMAIN}" \
            -e CONF_SPACE="${CONF_SPACE}" \
            -e CONF_USER="${CONF_USER}" \
            -e CONF_TOKEN="${CONF_TOKEN}" \
            -e COMMIT_MSG="${COMMIT_MSG}" \
            -e COMMIT_DIFF="${COMMIT_DIFF}" \
            -e COMMIT_HASH="${COMMIT_HASH}" \
            -e COMMIT_AUTHOR="${COMMIT_AUTHOR}" \
            -e PROJECT_NAME="${PROJECT_NAME}" \
            -e CHANGELOG_FORMAT="${CHANGELOG_FORMAT}" \
            -e VERSION="${VERSION}" \
            -e STAGE_NAME="${STAGE_NAME}" \
            ${DOCKER_IMAGE}
        '''
      }
    }
  }

  post {
    always {
      // push logs & changelog back into GitHub
      script {
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
            cp ${OUTPUT_DIR}/changelog.md    logs/changelog_${COMMIT_HASH}.md      || true
            git add logs/*
            git commit -m "Add changelog + log for build ${BUILD_NUMBER} (${COMMIT_HASH})" || true
            git push https://${GIT_USERNAME}:${GIT_PASSWORD}@github.com/parthsharma2003/Genai_project.git main
          """
        }
      }
      archiveArtifacts artifacts: 'output/**, logs/**, release.diff', fingerprint: true, allowEmptyArchive: true
      echo 'Pipeline complete.'
    }
    failure {
      echo 'Pipeline failed. Check archived logs in logs/changelog_generator.log for details.'
    }
  }
}
