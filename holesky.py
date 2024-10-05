import pexpect
import os
import time
import sys
import subprocess

# 检查 cast 命令是否可用
def check_cast_command():
    try:
        subprocess.run(['/root/.foundry/bin/cast', '--version'], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        print("Error: 'cast' command not found or not executable.")
        sys.exit(1)

check_cast_command()

# 定义私钥和密码
password = "just1lovewrl"
home_dir = os.path.expanduser('~')
keystore_dir = os.path.join(home_dir, '.aligned_keystore')
keystore_path = os.path.join(keystore_dir, 'keystore0')
cast_path = '/root/.foundry/bin/cast'

def run_quiz(private_key):
    # 设置路径


    # 删除现有目录并创建新目录
    os.system(f'rm -rf {keystore_dir}')
    os.makedirs(keystore_dir, exist_ok=True)
    os.chmod(keystore_dir, 0o700)
    print(f"Created directory {keystore_dir}")

    # 导入钱包并输入私钥和密码
    try:
        child = pexpect.spawn(f'{cast_path} wallet import {keystore_path} --interactive')
        child.logfile = sys.stdout.buffer  # 这将打印所有输出
        child.expect('Enter private key:')
        child.sendline(private_key)
        child.expect('Enter password:')
        child.sendline(password)
        index = child.expect(['Repeat password:', pexpect.EOF])
        if index == 0:
            child.sendline(password)
        elif index == 1:
            print("Wallet import completed without repeating password.")
        child.expect(pexpect.EOF)
        print("Wallet imported successfully.")
    except pexpect.ExceptionPexpect as e:
        print(f"Error during wallet import: {e}")
        print(f"Before: {child.before}")
        print(f"After: {child.after}")
        sys.exit(1)

    time.sleep(5)

    # 执行make命令并输入选项
    child = pexpect.spawn(f'make answer_quiz KEYSTORE_PATH={keystore_path}')
    child.logfile = sys.stdout.buffer  # 打印所有输出

    try:
        child.expect('Enter keystore password:')
        child.sendline(password)
        child.expect('If you already deposited Ethereum to Aligned before, this is not needed')
        child.sendline('y')
        child.expect('Satoshi Nakamoto')
        child.sendline('c')
        child.expect('Pacific')
        child.sendline('c')
        child.expect('Green')
        child.sendline('a')
        
        print("Waiting for proof generation. This may take several minutes...")
        
        # 设置一个较长的超时时间，例如 30 分钟
        timeout = 1800  # 30 分钟 = 1800 秒
        
        try:
            index = child.expect(['Do you want to continue', 'Proof generated successfully'], timeout=timeout)
            if index == 0:
                print("Proof generation completed. Proceeding to next step.")
            elif index == 1:
                print("Proof generated successfully!")
        except pexpect.TIMEOUT:
            print(f"Waited for {timeout} seconds, but proof generation is still not complete.")
            print("Continuing to the next step...")

        child.sendline('y')
        print("Final step initiated. This may take a while...")
        
        # 设置一个较长的超时时间，例如 60 分钟
        final_timeout = 600  # 60 分钟 = 3600 秒
        
        try:
            index = child.expect([pexpect.EOF, 'Proof submitted and verified successfully'], timeout=final_timeout)
            if index == 0:
                print("Process completed.")
            elif index == 1:
                print("Proof submitted and verified successfully!")
                child.expect(pexpect.EOF, timeout=300)
        except pexpect.TIMEOUT:
            print(f"Waited for {final_timeout} seconds, but the process is still not complete.")
            print("The script will now exit. Please check the process manually.")

        print("Script completed successfully.")
    except pexpect.ExceptionPexpect as e:
        print(f"Error during quiz: {e}")
        print(f"Before: {child.before}")
        print(f"After: {child.after}")
        sys.exit(1)

def read_private_keys(file_path):
    with open(file_path, 'r') as file:
        return [line.strip() for line in file if line.strip()]

def main():
    private_keys = read_private_keys('/root/aligned_layer/examples/zkquiz/privite_key.csv')
    
    for i, private_key in enumerate(private_keys, 1):
        print(f"Running quiz for private key {i}/{len(private_keys)}")
        run_quiz(private_key)
        print("Waiting 20 seconds before next run...")
        time.sleep(20)

if __name__ == "__main__":
    main()
