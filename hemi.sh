#!/bin/bash

# 私钥列表
PRIVATE_KEYS=(
"PRIVATE_KEYS01"
"PRIVATE_KEYS02"
"PRIVATE_KEYS03"
"PRIVATE_KEYS04"
)
# 获取私钥数量
NUM_KEYS=${#PRIVATE_KEYS[@]}

# 设定所需用户数量
REQUIRED_USERS=$NUM_KEYS

# 检查私钥数量是否满足要求
if [ "$NUM_KEYS" -lt "$REQUIRED_USERS" ]; then
    echo "PRIVATE_KEYS数组中的私钥数量不足"
    exit 1
fi

# 循环创建用户并置启动脚本
for i in $(seq 1 "$REQUIRED_USERS"); do
    USERNAME="user$i"
    USER_KEY="${PRIVATE_KEYS[$((i-1))]}"

    # 创建用户，如果已存在则跳过
    if id "$USERNAME" &>/dev/null; then
        echo "用户$USERNAME 已存在，跳过创建。"
    else
        sudo useradd -m "$USERNAME"
        if [ $? -ne 0 ]; then
            echo "创建用户$USERNAME 失败，请检查。"
            continue
        fi
        echo "已创建用户$USERNAME。"
    fi

    USER_HOME="/home/$USERNAME"

    # 为用户创建启动脚本
    sudo -u "$USERNAME" bash -c "cat > \"$USER_HOME/start_popmd.sh\" <<EOF
#!/bin/bash
curl -L -o ~/heminetwork.tar.gz https://github.com/hemilabs/heminetwork/releases/download/v0.4.3/heminetwork_v0.4.3_linux_amd64.tar.gz
tar -xvzf ~/heminetwork.tar.gz -C ~
rm ~/heminetwork.tar.gz
cd ~/heminetwork_v0.4.3_linux_amd64
export POPM_BTC_PRIVKEY='$USER_KEY'
export POPM_STATIC_FEE=51
export POPM_BFG_URL=wss://testnet.rpc.hemi.network/v1/ws/public
./popmd &
EOF"

    # 检查启动脚本是否成功创建
    if [ $? -ne 0 ]; then
        echo "为用户$USERNAME 创建启动脚本失败。"
        continue
    fi

    # 赋予脚本执行权限
    sudo chmod +x "$USER_HOME/start_popmd.sh"
    if [ $? -ne 0 ]; then
        echo "赋予用户$USERNAME 的启动脚本执行权限失败。"
        continue
    fi

    echo "已为用户$USERNAME 创建并赋予启动脚本执行权限。"

    # 执行启动脚本以安装 popmd
    sudo -u "$USERNAME" bash "$USER_HOME/start_popmd.sh"
    if [ $? -ne 0 ]; then
        echo "为用户$USERNAME 执行启动脚本失败。"
        continue
    fi

    echo "已为用户$USERNAME 安装 popmd。"

    # 创建 systemd 服务文件
    sudo tee "/etc/systemd/system/popmd-${USERNAME}.service" > /dev/null <<EOF
[Unit]
Description=popmd service for ${USERNAME}
After=network.target

[Service]
User=${USERNAME}
ExecStart=${USER_HOME}/heminetwork_v0.4.3_linux_amd64/popmd
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    # 检查服务文件是否成功创建
    if [ $? -ne 0 ]; then
        echo "为用户$USERNAME 创建 systemd 服务文件失败。"
        continue
    fi

    echo "已为用户$USERNAME 创建 systemd 服务文件。"

    # 启用 systemd 服务
    sudo systemctl enable "popmd-${USERNAME}.service"
    if [ $? -ne 0 ]; then
        echo "启用 popmd-${USERNAME}.service 失败。"
        continue
    fi

    echo "已启用 popmd-${USERNAME}.service。"
done

# 重新加载 systemd 守护进程
sudo systemctl daemon-reload
if [ $? -ne 0 ]; then
    echo "重新加载 systemd 守护进程失败。"
    exit 1
fi

# 启用并启动所有 popmd 服务
for i in $(seq 1 "$REQUIRED_USERS"); do
    USERNAME="user$i"
    SERVICE_NAME="popmd-${USERNAME}.service"

    echo "启动并检查 $SERVICE_NAME 服务..."
    sudo systemctl start "$SERVICE_NAME" &> /dev/null
    sudo systemctl enable "$SERVICE_NAME" &> /dev/null
    sudo systemctl status "$SERVICE_NAME" --no-pager &> /dev/null

    # 检查服务是否成功启动
    if sudo systemctl is-active --quiet "$SERVICE_NAME"; then
        echo "$SERVICE_NAME 已成功启动。"
    else
        echo "$SERVICE_NAME 启动失败。"
    fi
done

echo "所有用户的 popmd 服务已配置并启动完成。"
