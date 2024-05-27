import platform


def detect_os():
    
    os_name = platform.system()
    if os_name == "Darwin":
        print("You are using macOS.")
        return "mac"
    elif os_name == "Linux":
        print("You are using Linux.")
        return "linux"


if __name__ == "__main__":
    re = detect_os()
    print(re)
