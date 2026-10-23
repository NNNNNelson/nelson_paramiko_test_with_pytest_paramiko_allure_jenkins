// =================================================================
// paramiko 集成测试 Jenkins Pipeline (Windows 版)
// 使用方式 1（当前）: Jenkins 新建 Pipeline Job → Pipeline script → 粘贴运行
// 使用方式 2（稳定后）: Jenkins Job → Pipeline script from SCM → 指向此文件
// =================================================================

pipeline {
    agent any

    // SSH_HOST 不是敏感凭据，直接写在 environment 里注入
    // SSH_USER / SSH_PWD 仍然走 Jenkins Credentials + withCredentials
    environment {
        SSH_HOST = '127.0.0.1'
    }

    options {
        timestamps()
        timeout(time: 30, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
    }

    stages {

        // ------------------------------------------------------------
        // Stage 1: 确认环境 (打印工具版本，方便排查)
        // SCM 模式下 Jenkins 自动把代码 checkout 到 WORKSPACE
        // 这里直接在 WORKSPACE 里跑，不需要硬编码本地路径
        // ------------------------------------------------------------
        stage('Verify Environment') {
            steps {
                bat '''
                    echo ============================================
                    echo WORKSPACE: %WORKSPACE%
                    echo ============================================
                '''
                bat 'python --version'
                bat 'uv --version'
                bat 'allure --version'
                bat 'git --version'
            }
        }

        // ------------------------------------------------------------
        // Stage 2: 安装依赖
        // ------------------------------------------------------------
        stage('Install Dependencies') {
            steps {
                bat 'uv sync --all-extras'
            }
        }

        // ------------------------------------------------------------
        // Stage 3: 跑测试 (注入 SSH 凭据)
        // SSH_HOST  已在顶层 environment block 注入
        // SSH_USER / SSH_PWD 通过 Jenkins Credentials + withCredentials 注入
        // conftest.py 里的 os.getenv() 会从这些环境变量里取值
        // credentialsId 必须与 Jenkins → Credentials 中存的 ID 一致
        // ------------------------------------------------------------
        stage('Run Tests') {
            steps {
                bat 'if exist reports rmdir /s /q reports'
                bat 'if exist allure-results rmdir /s /q allure-results'

                withCredentials([
                    usernamePassword(
                        credentialsId: 'paramiko-ssh-creds',
                        usernameVariable: 'SSH_USER',
                        passwordVariable: 'SSH_PWD'
                    )
                ]) {
                    bat 'uv run pytest'
                }
            }
        }

        // ------------------------------------------------------------
        // Stage 4: 发布 pytest-html 报告
        // 依赖插件: HTML Publisher
        // reportDir 改为 WORKSPACE 相对路径
        // ------------------------------------------------------------
        stage('Publish HTML Report') {
            steps {
                publishHTML(target: [
                    allowMissing: true,
                    alwaysLinkToLastBuild: true,
                    keepAll: true,
                    reportDir: 'reports',
                    reportFiles: 'report.html',
                    reportName: 'Pytest HTML Report'
                ])
            }
        }

        // ------------------------------------------------------------
        // Stage 5: 生成 Allure 报告
        // 依赖插件: Allure (新版 org.allurereport.jenkins)
        // 前置配置: Manage Jenkins → Tools → Allure installations → allure-2.46
        // 语法要点:
        //   results = 对象数组 (支持多个 allure-results 目录合并)
        //   report  = 单个字符串 (输出目录)
        // ------------------------------------------------------------
        stage('Generate Allure Report') {
            steps {
                allure(
                    results: [[path: 'allure-results']],
                    report: 'allure-report'
                )
            }
        }
    }

    // 无论成功/失败都归档报告产物
    post {
        always {
            archiveArtifacts artifacts: 'reports\\**, allure-results\\**',
                             fingerprint: true,
                             allowEmptyArchive: true
        }
    }
}