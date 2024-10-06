import pexpect
import os
import time
import sys
import subprocess
import threading
from queue import Queue

# 检查 cast 命令是否可用
def check_cast_command():
    try:
        subprocess.run(['/root/.foundry/bin/cast', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("警告: 'cast' 命令未找到或不可执行。")
        return False
    return True

# 定义私钥和密码
password = "xxxxx"
home_dir = os.path.expanduser('~')
cast_path = '/root/.foundry/bin/cast'

def run_quiz(private_key, thread_id):
    keystore_dir = os.path.join(home_dir, f'.aligned_keystore_{thread_id}')
    keystore_path = os.path.join(keystore_dir, f'keystore{thread_id}')
    try:
        # 删除现有目录并创建新目录
        os.system(f'rm -rf {keystore_dir}')
        os.makedirs(keystore_dir, exist_ok=True)
        os.chmod(keystore_dir, 0o700)
        print(f"线程 {thread_id}: 创建目录 {keystore_dir}")

        # 导入钱包并输入私钥和密码
        child = pexpect.spawn(f'{cast_path} wallet import {keystore_path} --interactive')
        child.logfile = sys.stdout.buffer
        child.expect('Enter private key:')
        child.sendline(private_key)
        child.expect('Enter password:')
        child.sendline(password)
        index = child.expect(['Repeat password:', pexpect.EOF])
        if index == 0:
            child.sendline(password)
        elif index == 1:
            print(f"线程 {thread_id}: 钱包导入完成，无需重复密码。")
        child.expect(pexpect.EOF)
        print(f"线程 {thread_id}: 钱包导入成功。")

        time.sleep(5)

        # 执行make命令并输入选项
        child = pexpect.spawn(f'make answer_quiz KEYSTORE_PATH={keystore_path}')
        child.logfile = sys.stdout.buffer

        timeout = 120

        def expect_with_retry(pattern, max_retries=3):
            for attempt in range(max_retries):
                try:
                    return child.expect(pattern, timeout=timeout)
                except pexpect.TIMEOUT:
                    print(f"线程 {thread_id}: 等待 '{pattern}' 超时 (尝试 {attempt+1}/{max_retries})")
                    if attempt == max_retries - 1:
                        raise

        expect_with_retry('Enter keystore password:')
        child.sendline(password)
        time.sleep(4)

        expect_with_retry('If you already deposited Ethereum to Aligned before, this is not needed')
        child.sendline('y')
        time.sleep(2)

        expect_with_retry('Satoshi Nakamoto')
        child.sendline('c')
        time.sleep(2)

        expect_with_retry('Pacific')
        child.sendline('c')
        time.sleep(2)

        expect_with_retry('Green')
        child.sendline('a')
        time.sleep(2)

        print(f"线程 {thread_id}: 等待证明生成。这可能需要几分钟...")
        
        proof_timeout = 1800  # 30 分钟
        
        try:
            index = child.expect(['Do you want to continue', 'Proof generated successfully'], timeout=proof_timeout)
            if index == 0:
                print(f"线程 {thread_id}: 证明生成完成。继续下一步。")
            elif index == 1:
                print(f"线程 {thread_id}: 证明生成成功！")
        except pexpect.TIMEOUT:
            print(f"线程 {thread_id}: 等待 {proof_timeout} 秒后，证明生成仍未完成。")
            print(f"线程 {thread_id}: 继续下一步...")
        time.sleep(2)

        child.sendline('y')
        print(f"线程 {thread_id}: 最后一步已开始。这可能需要一段时间...")
        
        final_timeout = 3600  # 60 分钟
        
        try:
            index = child.expect([pexpect.EOF, 'Proof submitted and verified successfully'], timeout=final_timeout)
            if index == 0:
                print(f"线程 {thread_id}: 进程完成。")
            elif index == 1:
                print(f"线程 {thread_id}: 证明提交并验证成功！")
                child.expect(pexpect.EOF, timeout=300)
        except pexpect.TIMEOUT:
            print(f"线程 {thread_id}: 等待 {final_timeout} 秒后，进程仍未完成。")

        print(f"线程 {thread_id}: 脚本成功完成。")
    except pexpect.ExceptionPexpect as e:
        print(f"线程 {thread_id}: 在执行过程中发生错误: {e}")
        print(f"线程 {thread_id}: Before: {child.before}")
        print(f"线程 {thread_id}: After: {child.after}")
    except Exception as e:
        print(f"线程 {thread_id}: 发生未预期的错误: {e}")
    finally:
        print(f"线程 {thread_id}: 完成当前私钥的处理。")

def worker(queue, thread_id):
    while True:
        private_key = queue.get()
        if private_key is None:
            break
        print(f"线程 {thread_id}: 开始处理私钥")
        run_quiz(private_key, thread_id)
        queue.task_done()

def read_private_keys(file_path):
    try:
        with open(file_path, 'r') as file:
            return [line.strip() for line in file if line.strip()]
    except Exception as e:
        print(f"读取私钥文件时发生错误: {e}")
        return []

def main():
    if not check_cast_command():
        print("警告: 'cast' 命令不可用，但程序将继续执行。")

    private_keys = read_private_keys('/root/aligned_layer/examples/zkquiz/privite_key.csv')
    
    if not private_keys:
        print("没有读取到有效的私钥，程序退出。")
        return

    num_threads = min(4, len(private_keys))  # 使用最多4个线程，或者私钥数量如果少于4
    queue = Queue()

    # 创建工作线程
    threads = []
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(queue, i))
        t.start()
        threads.append(t)

    # 将私钥添加到队列
    for private_key in private_keys:
        queue.put(private_key)

    # 添加结束标记
    for _ in range(num_threads):
        queue.put(None)

    # 等待所有任务完成
    queue.join()

    # 等待所有线程结束
    for t in threads:
        t.join()

    print("所有私钥处理完成。")

if __name__ == "__main__":
    main()
