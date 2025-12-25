#!/bin/bash
set -e

# 检查是否安装了 sudo，如果没有则创建一个函数来模拟 sudo
if ! command -v sudo &> /dev/null; then
    echo "⚠️  未检测到 sudo 命令，将直接使用 root 权限执行命令"
    # 创建一个模拟 sudo 的函数
    sudo() {
        "$@"
    }
    export -f sudo
else
    echo "✅ 检测到 sudo 命令"
fi

echo "=========================================="
echo "🐳 欢迎使用轩辕镜像 Docker 一键安装配置脚本"
echo "=========================================="
echo "官方网站: https://xuanyuan.cloud/"
echo ""
echo "请选择操作模式："
echo "1) 一键安装配置（推荐）"
echo "2) 修改轩辕镜像专属加速地址"
echo ""
# 循环等待用户输入有效选择
while true; do
    read -p "请输入选择 [1/2]: " mode_choice
    
    if [[ "$mode_choice" == "1" ]]; then
        echo ""
        echo ">>> 模式：一键安装配置"
        
        # 检查是否已经安装了 Docker
        if command -v docker &> /dev/null; then
            DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
            echo ""
            echo "⚠️  检测到系统已安装 Docker 版本: $DOCKER_VERSION"
            echo ""
            echo "⚠️  重要提示："
            echo "   选择此选项将进行 Docker 升级或重装操作"
            echo "   这可能会影响现有的 Docker 容器和数据"
            echo "   建议在操作前备份重要的容器和数据"
            echo ""
            echo "请确认是否继续："
            echo "1) 确认继续安装/升级 Docker"
            echo "2) 返回选择菜单"
            echo ""
            
            # 循环等待用户输入有效选择
            while true; do
                read -p "请输入选择 [1/2]: " confirm_choice
                
                if [[ "$confirm_choice" == "1" ]]; then
                    echo ""
                    echo "✅ 用户确认继续，将进行 Docker 安装/升级..."
                    echo ""
                    break
                elif [[ "$confirm_choice" == "2" ]]; then
                    echo ""
                    echo "🔄 返回选择菜单..."
                    echo ""
                    # 重新显示菜单选项
                    echo "请选择操作模式："
                    echo "1) 一键安装配置（推荐）"
                    echo "2) 修改轩辕镜像专属加速地址"
                    echo ""
                    # 重置 mode_choice 以重新进入循环
                    mode_choice=""
                    break
                else
                    echo "❌ 无效选择，请输入 1 或 2"
                    echo ""
                fi
            done
            
            # 如果用户选择了返回菜单，继续外层循环
            if [[ "$confirm_choice" == "2" ]]; then
                continue
            fi
        fi
        
        echo ""
        break
    elif [[ "$mode_choice" == "2" ]]; then
        echo ""
        echo ">>> 模式：仅修改镜像加速地址"
        echo ""
        
        # 检查 Docker 是否已安装
        if ! command -v docker &> /dev/null; then
            echo "❌ 检测到 Docker 未安装！"
            echo ""
            echo "⚠️  风险提示："
            echo "   - 无法验证镜像加速配置是否生效"
            echo "   - 可能导致后续 Docker 操作失败"
            echo "   - 建议先完成 Docker 安装"
            echo ""
            echo "💡 建议：选择选项 1 进行一键安装配置"
            echo ""
            echo "已退出脚本，请重新运行并选择选项 1 进行完整安装配置"
            exit 1
        else
            # 检查 Docker 版本
            DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
            MAJOR_VERSION=$(echo $DOCKER_VERSION | cut -d. -f1)
            
            if [[ "$MAJOR_VERSION" -lt 20 ]]; then
                echo "⚠️  检测到 Docker 版本 $DOCKER_VERSION 低于 20.0"
                echo ""
                echo "⚠️  风险提示："
                echo "   - 低版本 Docker 可能存在安全漏洞"
                echo "   - 某些新功能可能不可用"
                echo "   - 建议升级到 Docker 20+ 版本"
                echo ""
                echo "💡 建议：选择选项 1 进行一键安装配置和升级"
                echo ""
                read -p "是否仍要继续？[y/N]: " continue_choice
                if [[ ! "$continue_choice" =~ ^[Yy]$ ]]; then
                    echo "已取消操作，建议选择选项 1 进行完整安装配置"
                    exit 0
                fi
            fi
        fi
        
        echo ""
        echo ">>> 配置轩辕镜像加速地址"
        echo ""
        echo "请选择版本："
        echo "1) 轩辕镜像免费版 (加速地址: docker.xuanyuan.me)"
        echo "2) 轩辕镜像专业版 (加速地址: 专属域名 + docker.xuanyuan.me)"
        # 循环等待用户输入有效选择
        while true; do
            read -p "请输入选择 [1/2]: " choice
            if [[ "$choice" == "1" || "$choice" == "2" ]]; then
                break
            else
                echo "❌ 无效选择，请输入 1 或 2"
                echo ""
            fi
        done
        
        mirror_list=""
        
        if [[ "$choice" == "2" ]]; then
            read -p "请输入您的轩辕镜像专属专属域名 (访问官网获取：https://xuanyuan.cloud): " custom_domain
            
            # 清理用户输入的域名，移除协议前缀
            custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
            
            # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
            if [[ "$custom_domain" == *.xuanyuan.run ]]; then
                custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
                mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://$custom_domain_dev",
  "https://docker.xuanyuan.me"
]
EOF
)
            else
                mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://docker.xuanyuan.me"
]
EOF
)
            fi
        else
            mirror_list=$(cat <<EOF
[
  "https://docker.xuanyuan.me"
]
EOF
)
        fi
        
        # 创建 Docker 配置目录
        mkdir -p /etc/docker
        
        # 备份现有配置
        if [ -f /etc/docker/daemon.json ]; then
            sudo cp /etc/docker/daemon.json /etc/docker/daemon.json.backup.$(date +%Y%m%d_%H%M%S)
            echo "✅ 已备份现有配置到 /etc/docker/daemon.json.backup.*"
        fi
        
        # 写入新配置
        
        # 根据用户选择设置 insecure-registries
        if [[ "$choice" == "2" ]]; then
          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "$custom_domain_dev",
  "docker.xuanyuan.me"
]
EOF
)
          else
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "docker.xuanyuan.me"
]
EOF
)
          fi
        else
          insecure_registries=$(cat <<EOF
[
  "docker.xuanyuan.me"
]
EOF
)
        fi

        cat <<EOF | tee /etc/docker/daemon.json
{
  "registry-mirrors": $mirror_list,
  "insecure-registries": $insecure_registries,
  "dns": ["119.29.29.29", "114.114.114.114"]
}
EOF
        
        echo "✅ 镜像加速配置已更新"
        echo ""
        echo "当前配置的镜像源："
        if [[ "$choice" == "2" ]]; then
            echo "  - https://$custom_domain (优先)"
            if [[ "$custom_domain" == *.xuanyuan.run ]]; then
                custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
                echo "  - https://$custom_domain_dev (备用)"
            fi
            echo "  - https://docker.xuanyuan.me (备用)"
        else
            echo "  - https://docker.xuanyuan.me"
        fi
        echo ""
        
        # 如果 Docker 服务正在运行，重启以应用配置
        if systemctl is-active --quiet docker 2>/dev/null; then
            echo "正在重启 Docker 服务以应用新配置..."
            systemctl daemon-reexec || true
            systemctl restart docker || true
            
            # 等待服务启动
            sleep 3
            
            if systemctl is-active --quiet docker; then
                echo "✅ Docker 服务重启成功，新配置已生效"
            else
                echo "❌ Docker 服务重启失败，请手动重启"
            fi
        else
            echo "⚠️  Docker 服务未运行，配置将在下次启动时生效"
        fi
        
        echo ""
        echo "🎉 镜像加速配置完成！"
        exit 0
    else
        echo "❌ 无效选择，请输入 1 或 2"
        echo ""
    fi
done

# 检测 macOS 和 Windows 系统
DETECTED_OS=$(uname -s 2>/dev/null || echo "Unknown")

# macOS 检测
if [[ "$DETECTED_OS" == "Darwin" ]]; then
  echo "🍎 检测到 macOS 系统"
  echo ""
  echo "=========================================="
  echo "⚠️  macOS 不支持此 Linux 安装脚本"
  echo "=========================================="
  echo ""
  echo "📋 macOS 安装 Docker 的正确方式："
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "方法一：使用 Homebrew 安装（推荐）"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  1. 如果未安装 Homebrew，先安装："
  echo "     /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  echo ""
  echo "  2. 使用 Homebrew 安装 Docker Desktop："
  echo "     brew install --cask docker"
  echo ""
  echo "  3. 启动 Docker Desktop："
  echo "     打开「应用程序」文件夹，双击 Docker 图标"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "方法二：下载官方安装包"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  访问：https://www.docker.com/products/docker-desktop"
  echo "  下载 Docker Desktop for Mac (Apple Silicon 或 Intel)"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🚀 配置轩辕镜像加速"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  1. 启动 Docker Desktop"
  echo "  2. 点击菜单栏 Docker 图标 → Settings (设置)"
  echo "  3. 选择 Docker Engine"
  echo "  4. 在 JSON 配置中添加："
  echo ""
  echo '  {'
  echo '    "registry-mirrors": ['
  echo '      "https://docker.xuanyuan.me"'
  echo '    ],'
  echo '    "insecure-registries": ['
  echo '      "docker.xuanyuan.me"'
  echo '    ]'
  echo '  }'
  echo ""
  echo "  5. 点击 Apply & Restart（应用并重启）"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📚 更多信息"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  官方网站：https://xuanyuan.cloud/"
  echo "  Docker 文档：https://docs.docker.com/desktop/install/mac-install/"
  echo ""
  echo "=========================================="
  exit 0
fi

# Windows 检测（Git Bash、WSL、Cygwin、MSYS2 等）
if [[ "$DETECTED_OS" == MINGW* ]] || [[ "$DETECTED_OS" == MSYS* ]] || [[ "$DETECTED_OS" == CYGWIN* ]]; then
  echo "🪟 检测到 Windows 系统"
  echo ""
  echo "=========================================="
  echo "⚠️  Windows 不支持此 Linux 安装脚本"
  echo "=========================================="
  echo ""
  echo "📋 Windows 安装 Docker 的正确方式："
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "方法一：Docker Desktop（推荐）"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  1. 访问官方网站："
  echo "     https://www.docker.com/products/docker-desktop"
  echo ""
  echo "  2. 下载 Docker Desktop for Windows"
  echo ""
  echo "  3. 运行安装程序并按提示完成安装"
  echo ""
  echo "  4. 重启计算机（如果需要）"
  echo ""
  echo "  📌 系统要求："
  echo "     - Windows 10/11 64位专业版、企业版或教育版"
  echo "     - 启用 WSL 2（Windows Subsystem for Linux 2）"
  echo "     - 启用 Hyper-V 和容器功能"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "方法二：在 WSL 2 中使用（高级用户）"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  1. 安装 WSL 2："
  echo "     wsl --install"
  echo ""
  echo "  2. 安装 Ubuntu 或其他 Linux 发行版"
  echo ""
  echo "  3. 在 WSL 2 中运行本安装脚本："
  echo "     bash <(curl -fsSL https://xuanyuan.cloud/docker.sh)"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "🚀 配置轩辕镜像加速"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  1. 启动 Docker Desktop"
  echo "  2. 点击系统托盘 Docker 图标 → Settings (设置)"
  echo "  3. 选择 Docker Engine"
  echo "  4. 在 JSON 配置中添加："
  echo ""
  echo '  {'
  echo '    "registry-mirrors": ['
  echo '      "https://docker.xuanyuan.me"'
  echo '    ],'
  echo '    "insecure-registries": ['
  echo '      "docker.xuanyuan.me"'
  echo '    ]'
  echo '  }'
  echo ""
  echo "  5. 点击 Apply & Restart（应用并重启）"
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "📚 更多信息"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  官方网站：https://xuanyuan.cloud/"
  echo "  Docker 文档：https://docs.docker.com/desktop/install/windows-install/"
  echo "  WSL 2 安装：https://docs.microsoft.com/windows/wsl/install"
  echo ""
  echo "=========================================="
  exit 0
fi

echo ">>> [1/8] 检查系统信息..."
OS=$(awk -F= '/^ID=/{print $2}' /etc/os-release | tr -d '"')
ARCH=$(uname -m)
VERSION_ID=$(awk -F= '/^VERSION_ID=/{print $2}' /etc/os-release | tr -d '"')
echo "系统: $OS $VERSION_ID 架构: $ARCH"

# 针对 Debian 10 和 Ubuntu 16.04 显示特殊提示
if [[ "$OS" == "debian" && "$VERSION_ID" == "10" ]]; then
  echo ""
  echo "⚠️  检测到 Debian 10 (Buster) 系统"
  echo "📋 系统状态说明："
  echo "   - Debian 10 已于 2022 年 8 月结束生命周期"
  echo "   - 官方软件源已迁移到 archive.debian.org"
  echo "   - 本脚本将自动配置国内镜像源以提高下载速度"
  echo "   - 建议考虑升级到 Debian 11+ 或 Ubuntu 20.04+"
  echo ""
  echo "🚀 优化措施："
  echo "   - 使用阿里云/腾讯云/华为云镜像源"
  echo "   - 自动检测并切换可用的镜像源"
  echo "   - 使用二进制安装方式避免包依赖问题"
  echo ""
elif [[ "$OS" == "ubuntu" && "$VERSION_ID" == "16.04" ]]; then
  echo ""
  echo "⚠️  检测到 Ubuntu 16.04 (Xenial) 系统"
  echo "📋 系统状态说明："
  echo "   - Ubuntu 16.04 已于 2021 年 4 月结束标准支持"
  echo "   - Docker 官方仓库缺少部分新组件（如 docker-buildx-plugin）"
  echo "   - 本脚本将使用二进制安装方式以确保兼容性"
  echo "   - 强烈建议升级到 Ubuntu 20.04 LTS 或 Ubuntu 22.04 LTS"
  echo ""
  echo "🚀 优化措施："
  echo "   - 使用 Docker 二进制包直接安装"
  echo "   - 自动配置多个国内镜像源"
  echo "   - 跳过不兼容的组件安装"
  echo ""
elif [[ "$OS" == "centos" && "$VERSION_ID" == "7" ]]; then
  echo ""
  echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
  echo "⚠️  重要提醒：CentOS 7 生命周期已结束"
  echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
  echo "⚠️  📅 2024 年 6 月 30 日：CentOS 7 结束生命周期（EOL）"
  echo "⚠️  "
  echo "⚠️  之后，不再接收官方更新或安全补丁"
  echo "⚠️  建议升级到受支持的操作系统版本"
  echo "⚠️  "
  echo "⚠️  推荐替代方案："
  echo "⚠️    - Rocky Linux 8/9（CentOS 的社区替代品）"
  echo "⚠️    - AlmaLinux 8/9（企业级长期支持）"
  echo "⚠️    - CentOS Stream 8/9（滚动发布版本）"
  echo "⚠️    - Red Hat Enterprise Linux 8/9（商业支持）"
  echo "⚠️  "
  echo "⚠️  当前将使用归档源继续安装，但强烈建议尽快升级系统"
  echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
  echo ""
elif [[ "$OS" == "centos" && "$VERSION_ID" == "8" ]]; then
  echo ""
  echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
  echo "⚠️  重要提醒：CentOS 8 生命周期已结束"
  echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
  echo "⚠️  📅 2021 年 12 月 31 日：CentOS 8 结束生命周期（EOL）"
  echo "⚠️  "
  echo "⚠️  之后，不再接收官方更新或安全补丁"
  echo "⚠️  建议升级到受支持的操作系统版本"
  echo "⚠️  "
  echo "⚠️  推荐替代方案："
  echo "⚠️    - Rocky Linux 8/9（CentOS 的社区替代品）"
  echo "⚠️    - AlmaLinux 8/9（企业级长期支持）"
  echo "⚠️    - CentOS Stream 8/9（滚动发布版本）"
  echo "⚠️    - Red Hat Enterprise Linux 8/9（商业支持）"
  echo "⚠️  "
  echo "⚠️  当前将使用归档源继续安装，但强烈建议尽快升级系统"
  echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
  echo ""
elif [[ "$OS" == "kylin" ]]; then
  echo ""
  echo "✅ 检测到银河麒麟操作系统 (Kylin Linux) V$VERSION_ID"
  echo "📋 系统信息："
  echo "   - Kylin Linux 基于 RHEL，与 CentOS/RHEL 兼容"
  echo "   - 使用 yum/dnf 包管理器"
  echo "   - 支持国内镜像源加速"
  echo ""
fi

echo ">>> [1.5/8] 检查 Docker 安装状态..."
if command -v docker &> /dev/null; then
    echo "检测到 Docker 已安装"
    DOCKER_VERSION=$(docker --version | grep -oE '[0-9]+\.[0-9]+' | head -1)
    echo "当前 Docker 版本: $DOCKER_VERSION"
    
    # 提取主版本号进行比较
    MAJOR_VERSION=$(echo $DOCKER_VERSION | cut -d. -f1)
    
    if [[ "$MAJOR_VERSION" -lt 20 ]]; then
        echo "警告: 当前 Docker 版本 $DOCKER_VERSION 低于 20.0"
        echo "建议升级到 Docker 20+ 版本以获得更好的性能和功能"
        read -p "是否要升级 Docker? [y/N]: " upgrade_choice
        
        if [[ "$upgrade_choice" =~ ^[Yy]$ ]]; then
            echo "用户选择升级 Docker，继续执行安装流程..."
        else
            echo "用户选择不升级，跳过 Docker 安装"
                    echo ">>> [5/8] 配置轩辕镜像加速..."
        
        # 循环等待用户选择镜像版本
        while true; do
            echo "请选择版本:"
            echo "1) 轩辕镜像免费版 (加速地址: docker.xuanyuan.me)"
            echo "2) 轩辕镜像专业版 (加速地址: 专属域名 + docker.xuanyuan.me)"
            read -p "请输入选择 [1/2]: " choice
            
            if [[ "$choice" == "1" || "$choice" == "2" ]]; then
                break
            else
                echo "❌ 无效选择，请输入 1 或 2"
                echo ""
            fi
        done
        
        mirror_list=""
        
        if [[ "$choice" == "2" ]]; then
          read -p "请输入您的轩辕镜像专属专属域名 (访问官网获取：https://xuanyuan.cloud): " custom_domain
          
          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://$custom_domain_dev",
  "https://docker.xuanyuan.me"
]
EOF
)
          else
            mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://docker.xuanyuan.me"
]
EOF
)
          fi
        else
          mirror_list=$(cat <<EOF
[
  "https://docker.xuanyuan.me"
]
EOF
)
        fi
        
        sudo mkdir -p /etc/docker

        # 根据用户选择设置 insecure-registries
        if [[ "$choice" == "2" ]]; then
          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "$custom_domain_dev",
  "docker.xuanyuan.me"
]
EOF
)
          else
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "docker.xuanyuan.me"
]
EOF
)
          fi
        else
          insecure_registries=$(cat <<EOF
[
  "docker.xuanyuan.me"
]
EOF
)
        fi

        cat <<EOF | sudo tee /etc/docker/daemon.json > /dev/null
{
  "registry-mirrors": $mirror_list,
  "insecure-registries": $insecure_registries,
  "dns": ["119.29.29.29", "114.114.114.114"]
}
EOF
        
        sudo systemctl daemon-reexec || true
        sudo systemctl restart docker || true
        
        echo ">>> [6/8] 安装完成！"
        echo "🎉Docker 镜像加速已配置完成"
        echo "轩辕镜像 - 国内开发者首选的专业 Docker 镜像下载加速服务平台"
        echo "官方网站: https://xuanyuan.cloud/"
        
        # 显示当前配置的镜像源
        echo ""
        echo "当前配置的镜像源："
        if [[ "$choice" == "2" ]]; then
            echo "  - https://$custom_domain (优先)"
            if [[ "$custom_domain" == *.xuanyuan.run ]]; then
                custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
                echo "  - https://$custom_domain_dev (备用)"
            fi
            echo "  - https://docker.xuanyuan.me (备用)"
        else
            echo "  - https://docker.xuanyuan.me"
        fi
        echo ""
        
        # 继续执行完整的流程，不在这里退出
        fi
    else
        echo "Docker 版本 $DOCKER_VERSION 满足要求 (>= 20.0)"
        echo "跳过 Docker 安装，直接配置镜像加速..."
        
        echo ">>> [5/8] 配置国内镜像加速..."
        
        # 循环等待用户选择镜像版本
        while true; do
            echo "请选择版本:"
            echo "1) 轩辕镜像免费版 (加速地址: docker.xuanyuan.me)"
            echo "2) 轩辕镜像专业版 (加速地址: 专属域名 + docker.xuanyuan.me)"
            read -p "请输入选择 [1/2]: " choice
            
            if [[ "$choice" == "1" || "$choice" == "2" ]]; then
                break
            else
                echo "❌ 无效选择，请输入 1 或 2"
                echo ""
            fi
        done
        
        mirror_list=""
        
        if [[ "$choice" == "2" ]]; then
          read -p "请输入您的轩辕镜像专属专属域名 (访问官网获取：https://xuanyuan.cloud): " custom_domain

          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://$custom_domain_dev",
  "https://docker.xuanyuan.me"
]
EOF
)
          else
            mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://docker.xuanyuan.me"
]
EOF
)
          fi
        else
          mirror_list=$(cat <<EOF
[
  "https://docker.xuanyuan.me"
]
EOF
)
        fi
        
        sudo mkdir -p /etc/docker

        # 根据用户选择设置 insecure-registries
        if [[ "$choice" == "2" ]]; then
          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "$custom_domain_dev",
  "docker.xuanyuan.me"
]
EOF
)
          else
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "docker.xuanyuan.me"
]
EOF
)
          fi
        else
          insecure_registries=$(cat <<EOF
[
  "docker.xuanyuan.me"
]
EOF
)
        fi

        cat <<EOF | sudo tee /etc/docker/daemon.json > /dev/null
{
  "registry-mirrors": $mirror_list,
  "insecure-registries": $insecure_registries,
  "dns": ["119.29.29.29", "114.114.114.114"]
}
EOF
        
        sudo systemctl daemon-reexec || true
        sudo systemctl restart docker || true
        
        echo ">>> [6/8] 安装完成！"
        echo "🎉Docker 镜像加速已配置完成"
        echo "轩辕镜像 - 国内开发者首选的专业 Docker 镜像下载加速服务平台"
        echo "官方网站: https://xuanyuan.cloud/"
        exit 0
    fi
else
    echo "未检测到 Docker，将进行全新安装"
fi

echo ">>> [2/8] 配置国内 Docker 源..."
# 将 OS 转换为小写进行比较（支持 openEuler、openeuler 等大小写形式）
OS_LOWER=$(echo "$OS" | tr '[:upper:]' '[:lower:]')
if [[ "$OS_LOWER" == "openeuler" ]]; then
  # openEuler (欧拉操作系统) 支持
  echo "检测到 openEuler (欧拉操作系统) $VERSION_ID"
  
  # 判断使用 dnf 还是 yum
  if [[ "${VERSION_ID%%.*}" -ge 22 ]]; then
    # openEuler 22+ 使用 dnf
    PKG_MANAGER="dnf"
    CENTOS_VERSION="9"
    echo "使用 dnf 包管理器 (openEuler $VERSION_ID 使用 CentOS 9 兼容源)"
  elif [[ "${VERSION_ID%%.*}" -ge 20 ]]; then
    # openEuler 20-21 使用 dnf，基于 CentOS 8
    PKG_MANAGER="dnf"
    CENTOS_VERSION="8"
    echo "使用 dnf 包管理器 (openEuler $VERSION_ID 使用 CentOS 8 兼容源)"
  else
    # openEuler 旧版本使用 yum，基于 CentOS 7
    PKG_MANAGER="yum"
    CENTOS_VERSION="7"
    echo "使用 yum 包管理器 (openEuler $VERSION_ID 使用 CentOS 7 兼容源)"
  fi
  
  sudo $PKG_MANAGER install -y ${PKG_MANAGER}-utils
  
  # 尝试多个国内镜像源（优先华为云，因为 openEuler 是华为开发）
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 openEuler 兼容的 CentOS 版本
  echo "正在创建 Docker 仓库配置 (使用 CentOS ${CENTOS_VERSION} 兼容源)..."
  
  # 源1: 华为云镜像（openEuler 是华为开发，优先使用华为云）
  echo "尝试配置华为云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo $PKG_MANAGER makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 华为云 Docker 源配置成功"
  else
    echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 阿里云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置阿里云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 阿里云 Docker 源配置成功"
    else
      echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo $PKG_MANAGER install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo $PKG_MANAGER install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 华为云镜像（优先）
      echo "尝试从华为云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从华为云镜像下载成功"
      else
        echo "❌ 华为云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 阿里云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从阿里云镜像下载..."
        if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从阿里云镜像下载成功"
        else
          echo "❌ 阿里云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 华为云镜像（优先）
  echo "尝试从华为云镜像下载..."
  if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从华为云镜像下载成功"
  else
    echo "❌ 华为云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 阿里云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从阿里云镜像下载..."
    if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从阿里云镜像下载成功"
    else
      echo "❌ 阿里云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo $PKG_MANAGER install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "opencloudos" ]]; then
  # OpenCloudOS 9 使用 dnf 而不是 yum
  sudo dnf install -y dnf-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 OpenCloudOS 9 兼容的版本
  echo "正在创建 Docker 仓库配置..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo dnf makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo dnf install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo dnf install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo dnf install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo dnf install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 阿里云镜像
  echo "尝试从阿里云镜像下载..."
  if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从阿里云镜像下载成功"
  else
    echo "❌ 阿里云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从华为云镜像下载..."
    if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从华为云镜像下载成功"
    else
      echo "❌ 华为云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo dnf install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "anolis" ]]; then
  # Anolis OS (龙蜥操作系统) 支持
  echo "检测到 Anolis OS (龙蜥操作系统) $VERSION_ID"
  
  # 判断使用 dnf 还是 yum
  if [[ "${VERSION_ID%%.*}" -ge 8 ]]; then
    # Anolis 8+ 使用 dnf
    PKG_MANAGER="dnf"
    CENTOS_VERSION="8"
    echo "使用 dnf 包管理器 (Anolis $VERSION_ID 基于 CentOS 8+)"
  else
    # Anolis 7 使用 yum
    PKG_MANAGER="yum"
    CENTOS_VERSION="7"
    echo "使用 yum 包管理器 (Anolis $VERSION_ID 基于 CentOS 7)"
  fi
  
  sudo $PKG_MANAGER install -y ${PKG_MANAGER}-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 Anolis 兼容的 CentOS 版本
  echo "正在创建 Docker 仓库配置 (使用 CentOS ${CENTOS_VERSION} 兼容源)..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo $PKG_MANAGER makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo $PKG_MANAGER install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo $PKG_MANAGER install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 阿里云镜像
  echo "尝试从阿里云镜像下载..."
  if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从阿里云镜像下载成功"
  else
    echo "❌ 阿里云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从华为云镜像下载..."
    if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从华为云镜像下载成功"
    else
      echo "❌ 华为云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo $PKG_MANAGER install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "alinux" ]]; then
  # Alinux (Alibaba Cloud Linux) 支持
  echo "检测到 Alibaba Cloud Linux (Alinux) $VERSION_ID"
  echo "基于 Anolis OS，阿里云深度优化的企业级操作系统"
  
  # 判断使用 dnf 还是 yum
  if [[ "${VERSION_ID%%.*}" -ge 3 ]]; then
    # Alinux 3+ 使用 dnf，基于 Anolis OS 8
    PKG_MANAGER="dnf"
    CENTOS_VERSION="8"
    echo "使用 dnf 包管理器 (Alinux $VERSION_ID 基于 Anolis OS 8 / CentOS 8)"
  else
    # Alinux 2 使用 yum，基于 Anolis OS 7
    PKG_MANAGER="yum"
    CENTOS_VERSION="7"
    echo "使用 yum 包管理器 (Alinux $VERSION_ID 基于 Anolis OS 7 / CentOS 7)"
  fi
  
  sudo $PKG_MANAGER install -y ${PKG_MANAGER}-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 Alinux 兼容的 CentOS 版本
  echo "正在创建 Docker 仓库配置 (使用 CentOS ${CENTOS_VERSION} 兼容源)..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo $PKG_MANAGER makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo $PKG_MANAGER install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo $PKG_MANAGER install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 阿里云镜像
  echo "尝试从阿里云镜像下载..."
  if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从阿里云镜像下载成功"
  else
    echo "❌ 阿里云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从华为云镜像下载..."
    if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从华为云镜像下载成功"
    else
      echo "❌ 华为云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo $PKG_MANAGER install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "fedora" ]]; then
  # Fedora 支持
  echo "检测到 Fedora $VERSION_ID"
  
  # 检查 Fedora 版本是否过期
  if [[ "${VERSION_ID%%.*}" -lt 38 ]]; then
    echo ""
    echo "⚠️  警告：Fedora $VERSION_ID 可能已结束生命周期"
    echo "📋 建议："
    echo "   - 升级到 Fedora 38+ 以获得最新的安全更新和软件包"
    echo "   - 或考虑使用 Rocky Linux / AlmaLinux（企业级长期支持）"
    echo ""
  fi
  
  # Fedora 使用 dnf 包管理器
  sudo dnf install -y dnf-plugins-core
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 Fedora 专用仓库
  echo "正在创建 Docker 仓库配置..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/fedora/\$releasever/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/fedora/gpg
EOF
  
  if sudo dnf makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/fedora/\$releasever/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/fedora/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/fedora/\$releasever/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/fedora/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/fedora/\$releasever/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/fedora/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/fedora/\$releasever/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/fedora/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/fedora/\$releasever/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/fedora/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo dnf install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo dnf install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo dnf install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo dnf install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败（可选组件）"
    fi
    
    if sudo dnf install -y docker-compose-plugin; then
      echo "✅ docker-compose-plugin 安装成功"
    else
      echo "❌ docker-compose-plugin 安装失败（可选组件）"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 检查是否已通过插件安装
  if command -v docker compose version &> /dev/null 2>&1; then
    echo "✅ Docker Compose (插件版本) 已安装"
  else
    # 安装独立版本的 docker-compose，使用多个备用下载源
    echo "正在下载 Docker Compose 独立版本..."
    
    # 尝试多个下载源
    DOCKER_COMPOSE_DOWNLOADED=false
    
    # 源1: 阿里云镜像
    echo "尝试从阿里云镜像下载..."
    if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从阿里云镜像下载成功"
    else
      echo "❌ 阿里云镜像下载失败，尝试下一个源..."
    fi
    
    # 源2: 腾讯云镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从腾讯云镜像下载..."
      if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从腾讯云镜像下载成功"
      else
        echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源3: 华为云镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从华为云镜像下载..."
      if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从华为云镜像下载成功"
      else
        echo "❌ 华为云镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源4: 中科大镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从中科大镜像下载..."
      if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从中科大镜像下载成功"
      else
        echo "❌ 中科大镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源5: 清华大学镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从清华大学镜像下载..."
      if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从清华大学镜像下载成功"
      else
        echo "❌ 清华大学镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源6: 网易镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从网易镜像下载..."
      if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从网易镜像下载成功"
      else
        echo "❌ 网易镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源7: 最后尝试 GitHub (如果网络允许)
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从 GitHub 下载..."
      if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从 GitHub 下载成功"
      else
        echo "❌ GitHub 下载失败"
      fi
    fi
    
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
      # 设置执行权限
      sudo chmod +x /usr/local/bin/docker-compose
      
      # 创建软链接到 PATH 目录
      sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
      
      echo "✅ Docker Compose 独立版本安装完成"
    else
      echo "⚠️  Docker Compose 独立版本安装失败"
      echo "您仍可以使用 'docker compose' 命令（如果插件已安装）"
    fi
  fi

elif [[ "$OS" == "rocky" ]]; then
  # Rocky Linux 9 使用 dnf 而不是 yum
  sudo dnf install -y dnf-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 Rocky Linux 9 兼容的版本
  echo "正在创建 Docker 仓库配置..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo dnf makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo dnf install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo dnf install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo dnf install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo dnf install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 阿里云镜像
  echo "尝试从阿里云镜像下载..."
  if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从阿里云镜像下载成功"
  else
    echo "❌ 阿里云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从华为云镜像下载..."
    if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从华为云镜像下载成功"
    else
      echo "❌ 华为云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo dnf install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "kylin" ]]; then
  # Kylin Linux (银河麒麟) 支持
  echo "检测到 Kylin Linux V$VERSION_ID"
  echo "Kylin Linux 基于 RHEL，与 CentOS/RHEL 兼容"
  
  # 判断使用 dnf 还是 yum，以及对应的 CentOS 版本
  if command -v dnf &> /dev/null; then
    # Kylin V10 通常基于 RHEL 8，但使用 dnf
    PKG_MANAGER="dnf"
    # 尝试 CentOS 8 源（Kylin V10 基于 RHEL 8）
    CENTOS_VERSION="8"
    echo "使用 dnf 包管理器 (Kylin V$VERSION_ID 基于 RHEL 8)"
  else
    # Kylin V7 使用 yum
    PKG_MANAGER="yum"
    CENTOS_VERSION="7"
    echo "使用 yum 包管理器 (Kylin V$VERSION_ID 基于 RHEL 7)"
  fi
  
  sudo $PKG_MANAGER install -y ${PKG_MANAGER}-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用兼容的 CentOS 版本
  echo "正在创建 Docker 仓库配置 (使用 CentOS ${CENTOS_VERSION} 兼容源)..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo $PKG_MANAGER makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo $PKG_MANAGER makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo $PKG_MANAGER install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo $PKG_MANAGER install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo $PKG_MANAGER install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 阿里云镜像
  echo "尝试从阿里云镜像下载..."
  if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从阿里云镜像下载成功"
  else
    echo "❌ 阿里云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从华为云镜像下载..."
    if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从华为云镜像下载成功"
    else
      echo "❌ 华为云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo $PKG_MANAGER install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "almalinux" ]]; then
  # AlmaLinux (CentOS 替代品) 支持
  echo "检测到 AlmaLinux $VERSION_ID"
  echo "AlmaLinux 是 RHEL 的 1:1 二进制兼容克隆，企业级长期支持"
  
  # AlmaLinux 使用 dnf 而不是 yum
  sudo dnf install -y dnf-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，使用 AlmaLinux 兼容的 CentOS 9 版本
  echo "正在创建 Docker 仓库配置 (使用 CentOS 9 兼容源)..."
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo dnf makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/9/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo dnf makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo dnf install -y containerd.io; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo dnf install -y docker-ce-cli; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo dnf install -y docker-ce; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo dnf install -y docker-buildx-plugin; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，使用多个备用下载源
  echo "正在下载 Docker Compose..."
  
  # 尝试多个下载源
  DOCKER_COMPOSE_DOWNLOADED=false
  
  # 源1: 阿里云镜像
  echo "尝试从阿里云镜像下载..."
  if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从阿里云镜像下载成功"
  else
    echo "❌ 阿里云镜像下载失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从腾讯云镜像下载..."
    if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从腾讯云镜像下载成功"
    else
      echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从华为云镜像下载..."
    if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从华为云镜像下载成功"
    else
      echo "❌ 华为云镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从中科大镜像下载..."
    if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从中科大镜像下载成功"
    else
      echo "❌ 中科大镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从清华大学镜像下载..."
    if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从清华大学镜像下载成功"
    else
      echo "❌ 清华大学镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从 GitHub 下载..."
    if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从 GitHub 下载成功"
    else
      echo "❌ GitHub 下载失败"
    fi
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if sudo dnf install -y docker-compose-plugin; then
      echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
      DOCKER_COMPOSE_DOWNLOADED=true
    else
      echo "❌ 包管理器安装也失败了"
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi

elif [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
  # 检查 Debian/Ubuntu 版本，为老版本提供兼容性支持
  if [[ ("$OS" == "debian" && ("$VERSION_ID" == "9" || "$VERSION_ID" == "10")) || ("$OS" == "ubuntu" && "$VERSION_ID" == "16.04") ]]; then
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      echo "⚠️  检测到 Debian 9 (Stretch)，使用兼容的安装方法..."
      echo "⚠️  注意：Debian 9 已于 2020年7月停止主线支持，2022年6月停止LTS支持"
      echo "⚠️  建议升级到 Debian 10 (Buster) 或更高版本"
    elif [[ "$OS" == "debian" && "$VERSION_ID" == "10" ]]; then
      echo "⚠️  检测到 Debian 10 (Buster)，使用兼容的安装方法..."
      echo "⚠️  注意：Debian 10 将于 2024年6月停止主线支持，建议考虑升级到 Debian 11+"
    elif [[ "$OS" == "ubuntu" && "$VERSION_ID" == "16.04" ]]; then
      echo "⚠️  检测到 Ubuntu 16.04 (Xenial)，使用兼容的安装方法..."
      echo "⚠️  注意：Ubuntu 16.04 已于 2021 年结束生命周期，将使用特殊处理..."
    fi
    
    # 清理损坏的软件源索引文件
    echo "正在清理损坏的软件源索引文件..."
    sudo rm -rf /var/lib/apt/lists/*
    sudo rm -rf /var/lib/apt/lists/partial/*
    
    # 强制清理 apt 缓存
    sudo apt-get clean
    sudo apt-get autoclean
    
    # 为 Debian 9/10 或 Ubuntu 16.04 配置更兼容的软件源
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      echo "正在配置 Debian 9 兼容的软件源..."
      
      # ⚠️ Debian 9 (Stretch) 生命周期结束警告
      echo ""
      echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
      echo "⚠️  重要提醒：Debian 9 (Stretch) 生命周期已结束"
      echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
      echo "⚠️  📅 2020 年 7 月：停止主线支持（EOL）"
      echo "⚠️  📅 2022 年 6 月：停止 LTS（长期支持）"
      echo "⚠️  "
      echo "⚠️  之后，不再在 deb.debian.org 和 security.debian.org 提供软件包"
      echo "⚠️  建议升级到至少 Debian 10 (Buster) 或更高版本"
      echo "⚠️  "
      echo "⚠️  当前将使用归档源继续安装，但强烈建议尽快升级系统"
      echo "⚠️  ═══════════════════════════════════════════════════════════════════════════════"
      echo ""
      
      # 备份原始源列表
      sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)
      
      # Debian 9 已停止支持，使用归档源
      echo "正在配置 Debian 9 归档源（官方源已停止支持）..."
      
      # 使用官方归档源（亲测可用）
      sudo tee /etc/apt/sources.list > /dev/null <<EOF
# Debian 9 (Stretch) 官方归档源 - 主要源
# ⚠️ 注意：Debian 9 已停止支持，建议升级到 Debian 10+ 或更高版本
deb http://archive.debian.org/debian stretch main contrib non-free
deb http://archive.debian.org/debian-security stretch/updates main contrib non-free

# 国内归档镜像源 - 备用源（速度快）
# 阿里云归档源
# deb http://mirrors.aliyun.com/debian-archive/debian stretch main contrib non-free
# deb http://mirrors.aliyun.com/debian-archive/debian-security stretch/updates main contrib non-free

# 清华大学归档源
# deb https://mirrors.tuna.tsinghua.edu.cn/debian-archive/debian stretch main contrib non-free
# deb https://mirrors.tuna.tsinghua.edu.cn/debian-archive/debian-security stretch/updates main contrib non-free
EOF
      
      echo "✅ Debian 9 归档源配置完成"
      echo "💡 建议：安装完成后考虑升级到 Debian 10 (Buster) 或更高版本"
    elif [[ "$VERSION_ID" == "10" ]]; then
      echo "正在配置 Debian 10 兼容的软件源..."
      
      # 备份原始源列表
      sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d_%H%M%S)
      
      # 使用国内镜像源替代 archive.debian.org，提高下载速度
      echo "正在配置国内镜像源以提高下载速度..."
      
      # 尝试配置阿里云镜像源
      sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 阿里云镜像源 - 主要源
deb http://mirrors.aliyun.com/debian/ buster main contrib non-free
deb http://mirrors.aliyun.com/debian-security/ buster/updates main contrib non-free
deb http://mirrors.aliyun.com/debian/ buster-updates main contrib non-free

# 备用源 - 腾讯云镜像
# deb http://mirrors.cloud.tencent.com/debian/ buster main contrib non-free
# deb http://mirrors.cloud.tencent.com/debian-security/ buster/updates main contrib non-free
# deb http://mirrors.cloud.tencent.com/debian/ buster-updates main contrib non-free

# 备用源 - 华为云镜像
# deb http://mirrors.huaweicloud.com/debian/ buster main contrib non-free
# deb http://mirrors.huaweicloud.com/debian-security/ buster/updates main contrib non-free
# deb http://mirrors.huaweicloud.com/debian/ buster-updates main contrib non-free

# 最后备用 - archive.debian.org（如果国内源都不可用）
# deb http://archive.debian.org/debian/ buster main
# deb http://archive.debian.org/debian-security/ buster/updates main
# deb http://archive.debian.org/debian/ buster-updates main
EOF
      
      echo "✅ Debian 10 国内镜像源配置完成"
    elif [[ "$OS" == "ubuntu" && "$VERSION_ID" == "16.04" ]]; then
      echo "正在配置 Ubuntu 16.04 兼容的软件源..."
      echo "⚠️  Ubuntu 16.04 官方支持已结束，建议升级到 Ubuntu 20.04 LTS 或更高版本"
      echo "✅ Ubuntu 16.04 软件源配置保持现状（通常已配置国内镜像源）"
    fi
    
    # 首先尝试安装基本工具
    echo "正在安装基本工具..."
    
    # 测试软件源可用性并自动切换
    echo "正在测试软件源可用性..."
    # Debian 9 需要忽略过期校验
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      if sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false 2>/dev/null; then
        echo "✅ 当前软件源可用"
      else
        echo "⚠️  当前软件源不可用，尝试切换到备用源..."
        
        # 尝试腾讯云镜像源
        DEBIAN_CODENAME="stretch"
        
        sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 腾讯云镜像源
deb http://mirrors.cloud.tencent.com/debian/ ${DEBIAN_CODENAME} main contrib non-free
deb http://mirrors.cloud.tencent.com/debian-security/ ${DEBIAN_CODENAME}/updates main contrib non-free
deb http://mirrors.cloud.tencent.com/debian/ ${DEBIAN_CODENAME}-updates main contrib non-free
EOF
        
        if sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false 2>/dev/null; then
          echo "✅ 腾讯云镜像源可用"
        else
          echo "⚠️  腾讯云镜像源也不可用，尝试华为云镜像源..."
          
          # 尝试华为云镜像源
          sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 华为云镜像源
deb http://mirrors.huaweicloud.com/debian/ ${DEBIAN_CODENAME} main contrib non-free
deb http://mirrors.huaweicloud.com/debian-security/ ${DEBIAN_CODENAME}/updates main contrib non-free
deb http://mirrors.huaweicloud.com/debian/ ${DEBIAN_CODENAME}-updates main contrib non-free
EOF
          
          if sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false 2>/dev/null; then
            echo "✅ 华为云镜像源可用"
          else
            echo "⚠️  所有国内镜像源都不可用，回退到 archive.debian.org..."
            
            # 回退到 archive.debian.org
            sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 官方归档源（速度较慢但稳定）
deb http://archive.debian.org/debian/ ${DEBIAN_CODENAME} main
deb http://archive.debian.org/debian-security/ ${DEBIAN_CODENAME}/updates main
deb http://archive.debian.org/debian/ ${DEBIAN_CODENAME}-updates main
EOF
            
            sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false || true
          fi
        fi
      fi
    else
      if sudo apt-get update --allow-unauthenticated 2>/dev/null; then
        echo "✅ 当前软件源可用"
      else
        echo "⚠️  当前软件源不可用，尝试切换到备用源..."
        
        # 尝试腾讯云镜像源
        if [[ "$OS" == "debian" && "$VERSION_ID" == "10" ]]; then
          DEBIAN_CODENAME="buster"
        else
          DEBIAN_CODENAME="buster"  # 默认使用 buster
        fi
        
        sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 腾讯云镜像源
deb http://mirrors.cloud.tencent.com/debian/ ${DEBIAN_CODENAME} main contrib non-free
deb http://mirrors.cloud.tencent.com/debian-security/ ${DEBIAN_CODENAME}/updates main contrib non-free
deb http://mirrors.cloud.tencent.com/debian/ ${DEBIAN_CODENAME}-updates main contrib non-free
EOF
        
        if sudo apt-get update --allow-unauthenticated 2>/dev/null; then
          echo "✅ 腾讯云镜像源可用"
        else
          echo "⚠️  腾讯云镜像源也不可用，尝试华为云镜像源..."
          
          # 尝试华为云镜像源
          sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 华为云镜像源
deb http://mirrors.huaweicloud.com/debian/ ${DEBIAN_CODENAME} main contrib non-free
deb http://mirrors.huaweicloud.com/debian-security/ ${DEBIAN_CODENAME}/updates main contrib non-free
deb http://mirrors.huaweicloud.com/debian/ ${DEBIAN_CODENAME}-updates main contrib non-free
EOF
          
          if sudo apt-get update --allow-unauthenticated 2>/dev/null; then
            echo "✅ 华为云镜像源可用"
          else
            echo "⚠️  所有国内镜像源都不可用，回退到 archive.debian.org..."
            
            # 回退到 archive.debian.org
            sudo tee /etc/apt/sources.list > /dev/null <<EOF
# 官方归档源（速度较慢但稳定）
deb http://archive.debian.org/debian/ ${DEBIAN_CODENAME} main
deb http://archive.debian.org/debian-security/ ${DEBIAN_CODENAME}/updates main
deb http://archive.debian.org/debian/ ${DEBIAN_CODENAME}-updates main
EOF
            
            sudo apt-get update --allow-unauthenticated || true
          fi
        fi
      fi
    fi
    
    # 尝试安装必要的依赖包
    echo "正在安装必要的依赖包..."
    if sudo apt-get install -y --allow-unauthenticated apt-transport-https ca-certificates gnupg lsb-release; then
      echo "✅ 必要依赖包安装成功"
    else
      echo "⚠️  依赖包安装失败，尝试逐个安装..."
      
      # 逐个安装依赖包
      if sudo apt-get install -y --allow-unauthenticated apt-transport-https; then
        echo "✅ apt-transport-https 安装成功"
      else
        echo "⚠️  apt-transport-https 安装失败"
      fi
      
      if sudo apt-get install -y --allow-unauthenticated ca-certificates; then
        echo "✅ ca-certificates 安装成功"
      else
        echo "⚠️  ca-certificates 安装失败"
      fi
      
      if sudo apt-get install -y --allow-unauthenticated gnupg; then
        echo "✅ gnupg 安装成功"
      else
        echo "⚠️  gnupg 安装失败"
      fi
      
      if sudo apt-get install -y --allow-unauthenticated lsb-release; then
        echo "✅ lsb-release 安装成功"
      else
        echo "⚠️  lsb-release 安装失败"
      fi
    fi
    
    # 尝试安装 dirmngr 和 curl
    if sudo apt-get install -y --allow-unauthenticated dirmngr; then
      echo "✅ dirmngr 安装成功"
    else
      echo "⚠️  dirmngr 安装失败，将使用备用方法"
    fi
    
    if sudo apt-get install -y --allow-unauthenticated curl; then
      echo "✅ curl 安装成功"
    else
      echo "⚠️  curl 安装失败，将使用备用方法"
    fi
    
    # 为 Debian 10 或 Ubuntu 16.04 跳过有问题的包安装，直接使用二进制安装
    if [[ "$VERSION_ID" == "10" || ("$OS" == "ubuntu" && "$VERSION_ID" == "16.04") ]]; then
      if [[ "$OS" == "debian" ]]; then
        echo "⚠️  Debian 10 检测到软件源问题，跳过包管理器安装，直接使用二进制安装..."
      else
        echo "⚠️  Ubuntu 16.04 的 Docker 仓库缺少某些新组件，使用二进制安装..."
      fi
      echo "正在下载 Docker 二进制包..."
      
      # 尝试从多个源下载 Docker 二进制包
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker CE 二进制安装成功"
        
        # 启动 Docker 服务
        echo "正在启动 Docker 服务..."
        sudo systemctl daemon-reload
        sudo systemctl enable docker
        
        # 尝试启动 Docker 服务
        if sudo systemctl start docker; then
          echo "✅ Docker 服务启动成功"
        else
          echo "❌ Docker 服务启动失败，正在诊断问题..."
          
          # 检查服务状态
          echo "Docker 服务状态："
          sudo systemctl status docker --no-pager -l
          
          # 检查日志
          echo "Docker 服务日志："
          sudo journalctl -u docker --no-pager -l --since "5 minutes ago"
          
          # 尝试手动启动 dockerd 进行调试
          echo "尝试手动启动 dockerd 进行调试..."
          sudo /usr/bin/dockerd --debug --log-level=debug &
          DOCKERD_PID=$!
          sleep 5
          
          # 检查 dockerd 是否成功启动
          if sudo kill -0 $DOCKERD_PID 2>/dev/null; then
            echo "✅ dockerd 手动启动成功，问题可能在 systemd 配置"
            sudo kill $DOCKERD_PID
          else
            echo "❌ dockerd 手动启动也失败，请检查系统兼容性"
          fi
          
          echo "故障排除建议："
          echo "1. 检查系统是否支持 Docker"
          echo "2. 检查是否有其他容器运行时冲突"
          echo "3. 检查系统资源是否充足"
          echo "4. 尝试重启系统后再次运行脚本"
          
          exit 1
        fi
        
        # 安装 Docker Compose
        echo ">>> [3.5/8] 安装 Docker Compose..."
        echo "正在下载 Docker Compose..."
        
        # 尝试多个下载源
        DOCKER_COMPOSE_DOWNLOADED=false
        
        # 直接使用 GitHub 官方源（最可靠）
        echo "正在从 GitHub 官方源下载 Docker Compose..."
        if sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose --connect-timeout 30 --max-time 120; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从 GitHub 官方源下载成功"
        else
          echo "❌ GitHub 官方源下载失败"
          echo "💡 建议检查网络连接或使用代理"
        fi
        
        if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
          sudo chmod +x /usr/local/bin/docker-compose
          sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
          echo "✅ Docker Compose 安装完成"
        else
          echo "❌ 所有 Docker Compose 下载源都失败"
          echo "💡 建议：可以稍后手动安装 Docker Compose"
          echo "   下载地址：https://github.com/docker/compose/releases"
        fi
        
        # 跳过后续的包管理器安装流程
        echo ">>> [4/8] Docker 安装完成，跳过包管理器安装流程..."
        echo "✅ Docker 已通过二进制方式安装成功"
        echo "✅ Docker Compose 已安装"
        echo "✅ Docker 服务已启动"
        
        # 直接进入镜像加速配置
        echo ">>> [5/8] 配置轩辕镜像加速..."
        
        # 循环等待用户选择镜像版本
        while true; do
            echo "请选择版本:"
            echo "1) 轩辕镜像免费版 (加速地址: docker.xuanyuan.me)"
            echo "2) 轩辕镜像专业版 (加速地址: 专属域名 + docker.xuanyuan.me)"
            read -p "请输入选择 [1/2]: " choice
            
            if [[ "$choice" == "1" || "$choice" == "2" ]]; then
                break
            else
                echo "❌ 无效选择，请输入 1 或 2"
                echo ""
            fi
        done
        
        mirror_list=""
        
        if [[ "$choice" == "2" ]]; then
          read -p "请输入您的轩辕镜像专属专属域名 (访问官网获取：https://xuanyuan.cloud): " custom_domain

          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://$custom_domain_dev",
  "https://docker.xuanyuan.me"
]
EOF
)
          else
            mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://docker.xuanyuan.me"
]
EOF
)
          fi
        else
          mirror_list=$(cat <<EOF
[
  "https://docker.xuanyuan.me"
]
EOF
)
        fi

        mkdir -p /etc/docker

        # 根据用户选择设置 insecure-registries
        if [[ "$choice" == "2" ]]; then
          # 清理用户输入的域名，移除协议前缀
          custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
          
          # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
          if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "$custom_domain_dev",
  "docker.xuanyuan.me"
]
EOF
)
          else
            insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "docker.xuanyuan.me"
]
EOF
)
          fi
        else
          insecure_registries=$(cat <<EOF
[
  "docker.xuanyuan.me"
]
EOF
)
        fi

        cat <<EOF | sudo tee /etc/docker/daemon.json > /dev/null
{
  "registry-mirrors": $mirror_list,
  "insecure-registries": $insecure_registries,
  "dns": ["119.29.29.29", "114.114.114.114"]
}
EOF
        
        sudo systemctl daemon-reexec || true
        sudo systemctl restart docker || true
        
        echo ">>> [6/8] 安装完成！"
        echo "🎉Docker 镜像加速已配置完成"
        echo "轩辕镜像 - 国内开发者首选的专业 Docker 镜像下载加速服务平台"
        echo "官方网站: https://xuanyuan.cloud/"
        
        # 显示当前配置的镜像源
        echo ""
        echo "当前配置的镜像源："
        if [[ "$choice" == "2" ]]; then
            echo "  - https://$custom_domain (优先)"
            if [[ "$custom_domain" == *.xuanyuan.run ]]; then
                custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
                echo "  - https://$custom_domain_dev (备用)"
            fi
            echo "  - https://docker.xuanyuan.me (备用)"
        else
            echo "  - https://docker.xuanyuan.me"
        fi
        echo ""
        
        echo "🎉 安装和配置完成！"
        echo ""
        echo "轩辕镜像 - 国内开发者首选的专业 Docker 镜像下载加速服务平台"
        echo "官方网站: https://xuanyuan.cloud/"
        exit 0
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
    
    # 如果 curl 安装失败，尝试使用 wget 作为备用
    if ! command -v curl &> /dev/null && ! command -v wget &> /dev/null; then
      echo "正在安装 wget 作为 curl 的备用..."
      apt-get install -y --allow-unauthenticated wget || true
    fi
    
    # 现在尝试更新过期的 GPG 密钥
    echo "正在更新过期的 GPG 密钥..."
    if command -v dirmngr &> /dev/null; then
      apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 648ACFD622F3D138 || true
      apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 0E98404D386FA1D9 || true
      apt-key adv --keyserver keyserver.ubuntu.com --recv-keys AA8E81B4331F7F50 || true
      apt-key adv --keyserver keyserver.ubuntu.com --recv-keys 112695A0E562B32A || true
      
      # 尝试使用不同的密钥服务器
      echo "尝试使用备用密钥服务器..."
      apt-key adv --keyserver pgpkeys.mit.edu --recv-keys 648ACFD622F3D138 || true
      apt-key adv --keyserver pgpkeys.mit.edu --recv-keys 0E98404D386FA1D9 || true
    else
      echo "⚠️  dirmngr 不可用，跳过 GPG 密钥更新"
    fi
    
    
    # 更新软件包列表，允许未认证的包，移除不支持的选项
    echo "正在更新软件包列表..."
    # Debian 9 需要忽略过期校验
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false || true
    else
      sudo apt-get update --allow-unauthenticated || true
    fi
    
    # 如果还是失败，尝试强制更新
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      if ! sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false; then
        echo "⚠️  软件源更新失败，尝试强制更新..."
        sudo apt-get update --allow-unauthenticated --fix-missing -o Acquire::Check-Valid-Until=false || true
      fi
    else
      if ! sudo apt-get update --allow-unauthenticated; then
        echo "⚠️  软件源更新失败，尝试强制更新..."
        sudo apt-get update --allow-unauthenticated --fix-missing || true
      fi
    fi
    
    # 安装必要的依赖包，允许未认证的包
    echo "正在安装必要的依赖包..."
    sudo apt-get install -y --allow-unauthenticated --fix-broken ca-certificates gnupg lsb-release apt-transport-https || true
    
    # 如果某些包安装失败，尝试逐个安装
    if ! dpkg -l | grep -q "ca-certificates"; then
      echo "尝试单独安装 ca-certificates..."
      sudo apt-get install -y --allow-unauthenticated ca-certificates || true
    fi
    
    if ! dpkg -l | grep -q "gnupg"; then
      echo "尝试单独安装 gnupg..."
      sudo apt-get install -y --allow-unauthenticated gnupg || true
    fi
    
    # 添加 Docker 官方 GPG 密钥
    echo "正在添加 Docker 官方 GPG 密钥..."
    if command -v curl &> /dev/null; then
      # 尝试从国内镜像下载 GPG 密钥
      if sudo curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | sudo apt-key add -; then
        echo "✅ 从阿里云镜像下载 Docker GPG 密钥成功"
      elif sudo curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/debian/gpg | sudo apt-key add -; then
        echo "✅ 从腾讯云镜像下载 Docker GPG 密钥成功"
      elif sudo curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/debian/gpg | sudo apt-key add -; then
        echo "✅ 从华为云镜像下载 Docker GPG 密钥成功"
      else
        echo "❌ 所有国内镜像都无法下载 Docker GPG 密钥"
      fi
    elif command -v wget &> /dev/null; then
      # 尝试从国内镜像下载 GPG 密钥
      if sudo wget -qO- https://mirrors.aliyun.com/docker-ce/linux/debian/gpg | sudo apt-key add -; then
        echo "✅ 从阿里云镜像下载 Docker GPG 密钥成功"
      elif sudo wget -qO- https://mirrors.cloud.tencent.com/docker-ce/linux/debian/gpg | sudo apt-key add -; then
        echo "✅ 从腾讯云镜像下载 Docker GPG 密钥成功"
      elif sudo wget -qO- https://mirrors.huaweicloud.com/docker-ce/linux/debian/gpg | sudo apt-key add -; then
        echo "✅ 从华为云镜像下载 Docker GPG 密钥成功"
      else
        echo "❌ 所有国内镜像都无法下载 Docker GPG 密钥"
      fi
    else
      echo "❌ 无法下载 Docker GPG 密钥，curl 和 wget 都不可用"
    fi
    
    # 添加 Docker 仓库（使用国内镜像源）
    echo "正在添加 Docker 仓库..."
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      DEBIAN_CODENAME="stretch"
    elif [[ "$OS" == "debian" && "$VERSION_ID" == "10" ]]; then
      DEBIAN_CODENAME="buster"
    else
      DEBIAN_CODENAME="stretch"  # 默认使用 stretch
    fi
    
    # 尝试配置国内 Docker 镜像源
    echo "deb [arch=$(dpkg --print-architecture)] https://mirrors.aliyun.com/docker-ce/linux/debian ${DEBIAN_CODENAME} stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # 再次更新，这次包含 Docker 仓库
    echo "正在更新包含 Docker 仓库的软件包列表..."
    # Debian 9 需要忽略过期校验
    if [[ "$OS" == "debian" && "$VERSION_ID" == "9" ]]; then
      sudo apt-get update --allow-unauthenticated -o Acquire::Check-Valid-Until=false || true
    else
      sudo apt-get update --allow-unauthenticated || true
    fi
    
    echo ">>> [3/8] 安装 Docker CE 兼容版本..."
    echo "正在安装 Docker CE..."
    sudo apt-get install -y --allow-unauthenticated --fix-broken docker-ce docker-ce-cli containerd.io || true
    
    # 检查 Docker 是否安装成功
    if command -v docker &> /dev/null; then
      echo "✅ Docker CE 安装成功"
    else
      echo "❌ Docker CE 安装失败，尝试备用方法..."
      # 尝试从多个源下载 Docker 二进制包
      echo "正在下载 Docker 二进制包..."
      DOCKER_BINARY_DOWNLOADED=false
      
      if command -v curl &> /dev/null; then
        # 源1: 阿里云镜像
        echo "尝试从阿里云镜像下载 Docker 二进制包..."
        if sudo curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从阿里云镜像下载成功"
        else
          echo "❌ 阿里云镜像下载失败，尝试下一个源..."
        fi
        
        # 源2: 腾讯云镜像
        if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
          echo "尝试从腾讯云镜像下载 Docker 二进制包..."
          if sudo curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
            DOCKER_BINARY_DOWNLOADED=true
            echo "✅ 从腾讯云镜像下载成功"
          else
            echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
          fi
        fi
        
        # 源3: 华为云镜像
        if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
          echo "尝试从华为云镜像下载 Docker 二进制包..."
          if sudo curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
            DOCKER_BINARY_DOWNLOADED=true
            echo "✅ 从华为云镜像下载成功"
          else
            echo "❌ 华为云镜像下载失败"
          fi
        fi
      elif command -v wget &> /dev/null; then
        # 源1: 阿里云镜像
        echo "尝试从阿里云镜像下载 Docker 二进制包..."
        if sudo wget -O /tmp/docker.tgz https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz --timeout=60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从阿里云镜像下载成功"
        else
          echo "❌ 阿里云镜像下载失败，尝试下一个源..."
        fi
        
        # 源2: 腾讯云镜像
        if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
          echo "尝试从腾讯云镜像下载 Docker 二进制包..."
          if sudo wget -O /tmp/docker.tgz https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz --timeout=60; then
            DOCKER_BINARY_DOWNLOADED=true
            echo "✅ 从腾讯云镜像下载成功"
          else
            echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
          fi
        fi
        
        # 源3: 华为云镜像
        if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
          echo "尝试从华为云镜像下载 Docker 二进制包..."
          if sudo wget -O /tmp/docker.tgz https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz --timeout=60; then
            DOCKER_BINARY_DOWNLOADED=true
            echo "✅ 从华为云镜像下载成功"
          else
            echo "❌ 华为云镜像下载失败"
          fi
        fi
      else
        echo "❌ 无法下载 Docker 二进制包，curl 和 wget 都不可用"
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" && -f /tmp/docker.tgz ]]; then
        echo "正在解压 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /tmp
        sudo cp /tmp/docker/* /usr/bin/
        sudo chmod +x /usr/bin/docker*
        echo "✅ Docker CE 二进制安装成功"
      else
        echo "❌ Docker 二进制下载失败"
      fi
    fi
    
    echo ">>> [3.5/8] 安装 Docker Compose 兼容版本..."
    # Debian 9 使用较老版本的 docker-compose
    echo "正在下载兼容的 Docker Compose..."
    
    DOCKER_COMPOSE_DOWNLOADED=false
    
    # 尝试从多个源下载兼容版本
    echo "正在尝试从多个源下载 Docker Compose 兼容版本..."
    
    # 源1: 阿里云镜像
    if command -v curl &> /dev/null; then
      echo "尝试从阿里云镜像下载兼容版本..."
      if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.25.5/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载兼容版本成功"
      fi
    elif command -v wget &> /dev/null; then
      echo "尝试从阿里云镜像下载兼容版本..."
      if sudo wget -O /usr/local/bin/docker-compose "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.25.5/docker-compose-linux-x86_64" --timeout=30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载兼容版本成功"
      fi
    fi
    
    # 源2: 腾讯云镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      if command -v curl &> /dev/null; then
        echo "尝试从腾讯云镜像下载兼容版本..."
        if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.25.5/docker-compose-linux-x86_64" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载兼容版本成功"
        fi
      elif command -v wget &> /dev/null; then
        echo "尝试从腾讯云镜像下载兼容版本..."
        if sudo wget -O /usr/local/bin/docker-compose "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.25.5/docker-compose-linux-x86_64" --timeout=30; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载兼容版本成功"
        fi
      fi
    fi
    
    # 源3: 华为云镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      if command -v curl &> /dev/null; then
        echo "尝试从华为云镜像下载兼容版本..."
        if curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.25.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从华为云镜像下载兼容版本成功"
        fi
      elif command -v wget &> /dev/null; then
        echo "尝试从华为云镜像下载兼容版本..."
        if sudo wget -O /usr/local/bin/docker-compose "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.25.5/docker-compose-$(uname -s)-$(uname -m)" --timeout=30; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从华为云镜像下载兼容版本成功"
        fi
      fi
    fi
    
    # 源4: 最后尝试 GitHub
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      if command -v curl &> /dev/null; then
        echo "尝试从 GitHub 下载兼容版本..."
        if sudo curl -L "https://github.com/docker/compose/releases/download/1.25.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从 GitHub 下载兼容版本成功"
        fi
      elif command -v wget &> /dev/null; then
        echo "尝试从 GitHub 下载兼容版本..."
        if sudo wget -O /usr/local/bin/docker-compose "https://github.com/docker/compose/releases/download/1.25.5/docker-compose-$(uname -s)-$(uname -m)" --timeout=30; then
          DOCKER_COMPOSE_DOWNLOADED=true
          echo "✅ 从 GitHub 下载兼容版本成功"
        fi
      fi
    fi
    
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "❌ GitHub 下载失败，尝试包管理器安装..."
      if sudo apt-get install -y --allow-unauthenticated docker-compose; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 通过包管理器安装 docker-compose 成功"
      else
        echo "❌ 包管理器安装也失败了"
      fi
    fi
    
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
      sudo chmod +x /usr/local/bin/docker-compose
      sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
      echo "✅ Docker Compose 兼容版本安装完成"
    else
      echo "❌ Docker Compose 安装失败"
    fi
    
  else
    # 现代版本的 Ubuntu/Debian 使用标准安装方法
    sudo apt-get update
    sudo apt-get install -y ca-certificates curl gnupg lsb-release

    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://mirrors.tencent.com/docker-ce/linux/$OS/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://mirrors.tencent.com/docker-ce/linux/$OS \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update

    echo ">>> [3/8] 安装 Docker CE 最新版..."
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin

    echo ">>> [3.5/8] 安装 Docker Compose..."
    # 安装最新版本的 docker-compose，使用多个备用下载源
    echo "正在下载 Docker Compose..."
    
    # 尝试多个下载源
    DOCKER_COMPOSE_DOWNLOADED=false
    
    # 源1: 阿里云镜像
    echo "尝试从阿里云镜像下载..."
    if sudo curl -L "https://mirrors.aliyun.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从阿里云镜像下载成功"
    else
      echo "❌ 阿里云镜像下载失败，尝试下一个源..."
    fi
    
    # 源2: 腾讯云镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从腾讯云镜像下载..."
      if sudo curl -L "https://mirrors.cloud.tencent.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从腾讯云镜像下载成功"
      else
        echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源3: 华为云镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从华为云镜像下载..."
      if sudo curl -L "https://mirrors.huaweicloud.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从华为云镜像下载成功"
      else
        echo "❌ 华为云镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源4: 中科大镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从中科大镜像下载..."
      if sudo curl -L "https://mirrors.ustc.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从中科大镜像下载成功"
      else
        echo "❌ 中科大镜像下载失败，尝试下一个源..."
      fi
    fi
    
    # 源5: 清华大学镜像
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从清华大学镜像下载..."
      if sudo curl -L "https://mirrors.tuna.tsinghua.edu.cn/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从清华大学镜像下载成功"
      else
        echo "❌ 清华大学镜像下载失败，尝试下一个源..."
      fi
    fi
    
  # 源6: 网易镜像
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "尝试从网易镜像下载..."
    if sudo curl -L "https://mirrors.163.com/docker-toolbox/linux/compose/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
      DOCKER_COMPOSE_DOWNLOADED=true
      echo "✅ 从网易镜像下载成功"
    else
      echo "❌ 网易镜像下载失败，尝试下一个源..."
    fi
  fi
  
  # 源7: 最后尝试 GitHub (如果网络允许)
    # 源7: 最后尝试 GitHub (如果网络允许)
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "尝试从 GitHub 下载..."
      if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 10 --max-time 30; then
        DOCKER_COMPOSE_DOWNLOADED=true
        echo "✅ 从 GitHub 下载成功"
      else
        echo "❌ GitHub 下载失败"
      fi
    fi
    
    # 检查是否下载成功
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
      echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
      
      # 使用包管理器作为备选方案
      if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
        if sudo apt-get install -y docker-compose-plugin; then
          echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
          DOCKER_COMPOSE_DOWNLOADED=true
        else
          echo "❌ 包管理器安装也失败了"
        fi
      elif [[ "$OS" == "centos" || "$OS" == "rhel" || "$OS" == "rocky" || "$OS" == "ol" ]]; then
        if sudo yum install -y docker-compose-plugin; then
          echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
          DOCKER_COMPOSE_DOWNLOADED=true
        else
          echo "❌ 包管理器安装也失败了"
        fi
      fi
    fi
    
    if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
      # 设置执行权限
      sudo chmod +x /usr/local/bin/docker-compose
      
      # 创建软链接到 PATH 目录
      sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
      
      echo "✅ Docker Compose 安装完成"
    else
      echo "❌ Docker Compose 安装失败，请手动安装"
      echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
    fi
  fi

elif [[ "$OS" == "centos" || "$OS" == "rhel" || "$OS" == "rocky" || "$OS" == "ol" ]]; then
  sudo yum install -y yum-utils
  
  # 尝试多个国内镜像源
  echo "正在配置 Docker 源..."
  DOCKER_REPO_ADDED=false
  
  # 创建Docker仓库配置文件，直接使用国内镜像地址
  echo "正在创建 Docker 仓库配置..."
  
  # 根据系统版本选择正确的仓库路径
  if [[ "$VERSION_ID" == "8" ]]; then
    CENTOS_VERSION="8"
    echo "检测到 CentOS/RHEL/Rocky Linux 8，使用 CentOS 8 仓库"
  elif [[ "$VERSION_ID" == "9" ]]; then
    CENTOS_VERSION="9"
    echo "检测到 CentOS/RHEL/Rocky Linux 9，使用 CentOS 9 仓库"
  else
    CENTOS_VERSION="7"
    echo "检测到 CentOS/RHEL/Rocky Linux 7，使用 CentOS 7 仓库"
  fi
  
  # 源1: 阿里云镜像
  echo "尝试配置阿里云 Docker 源..."
  sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.aliyun.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.aliyun.com/docker-ce/linux/centos/gpg
EOF
  
  if sudo yum makecache; then
    DOCKER_REPO_ADDED=true
    echo "✅ 阿里云 Docker 源配置成功"
  else
    echo "❌ 阿里云 Docker 源配置失败，尝试下一个源..."
  fi
  
  # 源2: 腾讯云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置腾讯云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.cloud.tencent.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo yum makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 腾讯云 Docker 源配置成功"
    else
      echo "❌ 腾讯云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源3: 华为云镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置华为云 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.huaweicloud.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.huaweicloud.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo yum makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 华为云 Docker 源配置成功"
    else
      echo "❌ 华为云 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源4: 中科大镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置中科大 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/7/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.ustc.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo yum makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 中科大 Docker 源配置成功"
    else
      echo "❌ 中科大 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源5: 清华大学镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置清华大学 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.tuna.tsinghua.edu.cn/docker-ce/linux/centos/gpg
EOF
    
    if sudo yum makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 清华大学 Docker 源配置成功"
    else
      echo "❌ 清华大学 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 源6: 网易镜像
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "尝试配置网易 Docker 源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://mirrors.163.com/docker-ce/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://mirrors.163.com/docker-ce/linux/centos/gpg
EOF
    
    if sudo yum makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 网易 Docker 源配置成功"
    else
      echo "❌ 网易 Docker 源配置失败，尝试下一个源..."
    fi
  fi
  
  # 如果所有国内源都失败，尝试官方源
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "所有国内源都失败，尝试官方源..."
    sudo tee /etc/yum.repos.d/docker-ce.repo > /dev/null <<EOF
[docker-ce-stable]
name=Docker CE Stable - \$basearch
baseurl=https://download.docker.com/linux/centos/${CENTOS_VERSION}/\$basearch/stable
enabled=1
gpgcheck=1
gpgkey=https://download.docker.com/linux/centos/gpg
EOF
    
    if sudo yum makecache; then
      DOCKER_REPO_ADDED=true
      echo "✅ 官方 Docker 源配置成功"
    else
      echo "❌ 官方 Docker 源也配置失败"
    fi
  fi
  
  if [[ "$DOCKER_REPO_ADDED" == "false" ]]; then
    echo "❌ 所有 Docker 源都配置失败，无法继续安装"
    echo "请检查网络连接或手动配置 Docker 源"
    exit 1
  fi

  echo ">>> [3/8] 安装 Docker CE 最新版..."
  
  # 尝试安装 Docker，如果失败则尝试逐个安装组件
  if sudo yum install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin --nobest; then
    echo "✅ Docker CE 安装成功"
  else
    echo "❌ 批量安装失败，尝试逐个安装组件..."
    
    # 逐个安装组件
    if sudo yum install -y containerd.io --nobest; then
      echo "✅ containerd.io 安装成功"
    else
      echo "❌ containerd.io 安装失败"
    fi
    
    if sudo yum install -y docker-ce-cli --nobest; then
      echo "✅ docker-ce-cli 安装成功"
    else
      echo "❌ docker-ce-cli 安装失败"
    fi
    
    if sudo yum install -y docker-ce --nobest; then
      echo "✅ docker-ce 安装成功"
    else
      echo "❌ docker-ce 安装失败"
    fi
    
    if sudo yum install -y docker-buildx-plugin --nobest; then
      echo "✅ docker-buildx-plugin 安装成功"
    else
      echo "❌ docker-buildx-plugin 安装失败"
    fi
    
    # 检查是否至少安装了核心组件
    if ! command -v docker &> /dev/null; then
      echo "❌ 包管理器安装完全失败，尝试二进制安装..."
      
      # 二进制安装备选方案
      echo "正在下载 Docker 二进制包..."
      
      # 尝试多个下载源
      DOCKER_BINARY_DOWNLOADED=false
      
      # 源1: 阿里云镜像
      echo "尝试从阿里云镜像下载 Docker 二进制包..."
      if curl -fsSL https://mirrors.aliyun.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
        DOCKER_BINARY_DOWNLOADED=true
        echo "✅ 从阿里云镜像下载成功"
      else
        echo "❌ 阿里云镜像下载失败，尝试下一个源..."
      fi
      
      # 源2: 腾讯云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从腾讯云镜像下载..."
        if curl -fsSL https://mirrors.cloud.tencent.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从腾讯云镜像下载成功"
        else
          echo "❌ 腾讯云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源3: 华为云镜像
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从华为云镜像下载..."
        if curl -fsSL https://mirrors.huaweicloud.com/docker-ce/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从华为云镜像下载成功"
        else
          echo "❌ 华为云镜像下载失败，尝试下一个源..."
        fi
      fi
      
      # 源4: 官方源
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "false" ]]; then
        echo "尝试从官方源下载..."
        if curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-20.10.24.tgz -o /tmp/docker.tgz --connect-timeout 10 --max-time 60; then
          DOCKER_BINARY_DOWNLOADED=true
          echo "✅ 从官方源下载成功"
        else
          echo "❌ 官方源下载失败"
        fi
      fi
      
      if [[ "$DOCKER_BINARY_DOWNLOADED" == "true" ]]; then
        echo "正在解压并安装 Docker 二进制包..."
        sudo tar -xzf /tmp/docker.tgz -C /usr/bin --strip-components=1
        sudo chmod +x /usr/bin/docker*
        
        # 创建 systemd 服务文件
        sudo tee /etc/systemd/system/docker.service > /dev/null <<EOF
[Unit]
Description=Docker Application Container Engine
Documentation=https://docs.docker.com
After=network-online.target firewalld.service time-set.target
Wants=network-online.target
Requires=docker.socket

[Service]
Type=notify
ExecStart=/usr/bin/dockerd -H fd://
ExecReload=/bin/kill -s HUP \$MAINPID
TimeoutStartSec=0
RestartSec=2
Restart=always
StartLimitBurst=3
StartLimitInterval=60s
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
TasksMax=infinity
Delegate=yes
KillMode=process
OOMScoreAdjust=-500

[Install]
WantedBy=multi-user.target
EOF

        # 创建 docker.socket 文件
        sudo tee /etc/systemd/system/docker.socket > /dev/null <<EOF
[Unit]
Description=Docker Socket for the API

[Socket]
ListenStream=/var/run/docker.sock
SocketMode=0660
SocketUser=root
SocketGroup=docker

[Install]
WantedBy=sockets.target
EOF

        # 创建 docker 用户组
        sudo groupadd docker 2>/dev/null || true
        
        echo "✅ Docker 二进制安装成功"
      else
        echo "❌ 所有下载源都失败，无法安装 Docker"
        echo "请检查网络连接或手动安装 Docker"
        exit 1
      fi
    fi
  fi
  
  sudo systemctl enable docker
  sudo systemctl start docker
  
  echo ">>> [3.5/8] 安装 Docker Compose..."
  # 安装最新版本的 docker-compose，直接使用 GitHub 官方源
  echo "正在下载 Docker Compose..."
  
  # 直接使用 GitHub 官方源（最可靠）
  echo "正在从 GitHub 官方源下载 Docker Compose..."
  if sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose --connect-timeout 30 --max-time 120; then
    DOCKER_COMPOSE_DOWNLOADED=true
    echo "✅ 从 GitHub 官方源下载成功"
  else
    echo "❌ GitHub 官方源下载失败"
    echo "💡 建议检查网络连接或使用代理"
  fi
  
  # 检查是否下载成功
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "false" ]]; then
    echo "❌ 所有下载源都失败了，尝试使用包管理器安装..."
    
    # 使用包管理器作为备选方案
    if [[ "$OS" == "ubuntu" || "$OS" == "debian" ]]; then
      if sudo apt-get install -y docker-compose-plugin; then
        echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
        DOCKER_COMPOSE_DOWNLOADED=true
      else
        echo "❌ 包管理器安装也失败了"
      fi
    elif [[ "$OS" == "centos" || "$OS" == "rhel" || "$OS" == "rocky" || "$OS" == "ol" ]]; then
      if sudo yum install -y docker-compose-plugin; then
        echo "✅ 通过包管理器安装 docker-compose-plugin 成功"
        DOCKER_COMPOSE_DOWNLOADED=true
      else
        echo "❌ 包管理器安装也失败了"
      fi
    fi
  fi
  
  if [[ "$DOCKER_COMPOSE_DOWNLOADED" == "true" ]]; then
    # 设置执行权限
    sudo chmod +x /usr/local/bin/docker-compose
    
    # 创建软链接到 PATH 目录
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    echo "✅ Docker Compose 安装完成"
  else
    echo "❌ Docker Compose 安装失败，请手动安装"
    echo "建议访问: https://docs.docker.com/compose/install/ 查看手动安装方法"
  fi
else
  echo "暂不支持该系统: $OS"
  exit 1
fi

echo ">>> [5/8] 配置国内镜像加速..."

# 循环等待用户选择镜像版本
while true; do
    echo "请选择版本:"
    echo "1) 轩辕镜像免费版 (加速地址: docker.xuanyuan.me)"
    echo "2) 轩辕镜像专业版 (加速地址: 专属域名 + docker.xuanyuan.me)"
    read -p "请输入选择 [1/2]: " choice
    
    if [[ "$choice" == "1" || "$choice" == "2" ]]; then
        break
    else
        echo "❌ 无效选择，请输入 1 或 2"
        echo ""
    fi
done

mirror_list=""

if [[ "$choice" == "2" ]]; then
  read -p "请输入您的轩辕镜像专属专属域名 (访问官网获取：https://xuanyuan.cloud): " custom_domain

  # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
  if [[ "$custom_domain" == *.xuanyuan.run ]]; then
    custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
    mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://$custom_domain_dev",
  "https://docker.xuanyuan.me"
]
EOF
)
  else
    mirror_list=$(cat <<EOF
[
  "https://$custom_domain",
  "https://docker.xuanyuan.me"
]
EOF
)
  fi
else
  mirror_list=$(cat <<EOF
[
  "https://docker.xuanyuan.me"
]
EOF
)
fi

sudo mkdir -p /etc/docker

# 根据用户选择设置 insecure-registries
if [[ "$choice" == "2" ]]; then
  # 清理用户输入的域名，移除协议前缀
  custom_domain=$(echo "$custom_domain" | sed 's|^https\?://||')
  
  # 检查是否输入的是 .run 地址，如果是则自动添加 .dev 地址
  if [[ "$custom_domain" == *.xuanyuan.run ]]; then
    custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
    insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "$custom_domain_dev",
  "docker.xuanyuan.me"
]
EOF
)
  else
    insecure_registries=$(cat <<EOF
[
  "$custom_domain",
  "docker.xuanyuan.me"
]
EOF
)
  fi
else
  insecure_registries=$(cat <<EOF
[
  "docker.xuanyuan.me"
]
EOF
)
fi

cat <<EOF | sudo tee /etc/docker/daemon.json > /dev/null
{
  "registry-mirrors": $mirror_list,
  "insecure-registries": $insecure_registries,
  "dns": ["119.29.29.29", "114.114.114.114"]
}
EOF

sudo systemctl daemon-reexec || true
sudo systemctl restart docker || true

echo ">>> [6/8] 安装完成！"
echo "🎉Docker 镜像加速已配置完成"
echo "轩辕镜像 - 国内开发者首选的专业 Docker 镜像下载加速服务平台"
echo "官方网站: https://xuanyuan.cloud/"

echo ">>> [7/8] 重载 Docker 配置并重启服务..."
sudo systemctl daemon-reexec || true
sudo systemctl restart docker || true

# 等待 Docker 服务完全启动
echo "等待 Docker 服务启动..."
sleep 3

# 验证 Docker 服务状态
if systemctl is-active --quiet docker; then
    echo "✅ Docker 服务已成功启动"
    echo "✅ 镜像加速配置已生效"
    
    # 显示当前配置的镜像源
    echo "当前配置的镜像源:"
    if [[ "$choice" == "2" ]]; then
        echo "  - https://$custom_domain (优先)"
        if [[ "$custom_domain" == *.xuanyuan.run ]]; then
            custom_domain_dev="${custom_domain%.xuanyuan.run}.xuanyuan.dev"
            echo "  - https://$custom_domain_dev (备用)"
        fi
        echo "  - https://docker.xuanyuan.me (备用)"
    else
        echo "  - https://docker.xuanyuan.me"
    fi
    
    echo ""
    echo "🎉 安装和配置完成！"
    echo ""
    echo "轩辕镜像 - 国内开发者首选的专业 Docker 镜像下载加速服务平台"
    echo "官方网站: https://xuanyuan.cloud/"
else
    echo "❌ Docker 服务启动失败，请检查配置"
    exit 1
fi