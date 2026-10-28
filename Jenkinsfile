// =================================================================
// paramiko 集成测试 Jenkins Pipeline (Windows 版)
// 使用方式 1（当前）: Jenkins 新建 Pipeline Job → Pipeline script → 粘贴运行
// 使用方式 2（稳定后）: Jenkins Job → Pipeline script from SCM → 指向此文件
// =================================================================

pipeline {
    agent any

    options {
        // 注意: 性能测试跑 2000 个文件 + 每个文件 md5sum 校验, 串行耗时约 2-5 分钟,
        // 所以 Pipeline 总超时设为 10 分钟（之前 3 分钟会导致 perf suite 被强杀）
        timeout(time: 10, unit: 'MINUTES')
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timestamps()
    }

    parameters {
        choice(
            name: 'TEST_SUITE',
            choices: ['all', 'smoke', 'integration', 'perf'],
            description: '选择要执行的测试套件'
        )
        booleanParam(
            name: 'FAIL_FAST',
            defaultValue: false,
            description: '第一个失败就停止?'
        )
        string(
            name: 'SSH_HOST_OVERRIDE',
            defaultValue: '',
            description: '留空用默认 127.0.0.1, 填了就覆盖'
        )
    }

    // SSH_HOST 不是敏感凭据，直接写在 environment 里注入
    // SSH_USER / SSH_PWD 仍然走 Jenkins Credentials + withCredentials
    environment {
        SSH_HOST = "${params.SSH_HOST_OVERRIDE ?: '127.0.0.1'}"
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

                // 彻底清空 allure-results, 只保留 history 目录
                // 之前用 forfiles 逐条删, 在 --maxfail 场景下会残留上一次构建的
                // result.json, 导致我们的 skipped 补全逻辑误判 "全部测试都已执行"
                // Allure Jenkins 插件会自动把 history/ 归档和恢复, 不用担心丢失
                bat '''
                    if exist allure-results rmdir /s /q allure-results
                    mkdir allure-results\\history
                '''

                withCredentials([
                    usernamePassword(
                        credentialsId: 'paramiko-ssh-creds',
                        usernameVariable: 'SSH_USER',
                        passwordVariable: 'SSH_PWD'
                    )
                ]) {
                    bat """
                        uv run pytest ^
                        ${params.TEST_SUITE == 'all' ? '' : '-m' + params.TEST_SUITE} ^
                        --maxfail=${params.FAIL_FAST ? 1 : 9999}
                    """
                }
            }
        }
    }

    // ============================================================
    // post { always {} } 块: 无论测试成功/失败都执行
    // 关键修复: 把 Allure 报告生成、HTML 报告发布都移到这里
    // 原因: Declarative Pipeline 默认上一个 stage 失败后
    //       后续 stage 全部跳过, 导致失败构建没有 Allure 报告,
    //       Trend 图只记录了成功构建的数据
    // ============================================================
    post {
        always {
            // ---- 1. 发布 pytest-html 报告 ----
            publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'reports',
                reportFiles: 'report.html',
                reportName: 'Pytest HTML Report'
            ])

            // ---- 2. 生成 Allure 报告 ----
            // 无论 pytest 成功还是失败, allure-results 里都有数据
            // (成功 = 全绿, 失败 = 部分 result.json 含 failed/broken 状态)
            // Allure 插件会自动从 archiveArtifacts 恢复 history,
            // 合并当前数据后生成完整的 trend 图
            allure(
                results: [[path: 'allure-results']],
                report: 'allure-report'
            )

            // ---- 3. 归档产物 ----
            // archiveArtifacts 归档 allure-results/**, 包括 history/
            // 这样下一次构建开始时, Allure 插件才能从中恢复历史数据
            archiveArtifacts artifacts: 'reports/**, allure-results/**',
                             allowEmptyArchive: true
        }
    }
}
