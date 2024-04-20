import random
import sys
import time
from selenium import webdriver
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from selenium.common.exceptions import TimeoutException


def login_and_save_cookies():
    # a new webdriver instance
    driver_path = "./driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://channels.weixin.qq.com/platform/post/create")

    # wait for the user to login
    input("登录完成按任意键继续")

    # save the cookies
    cookies = driver.get_cookies()
    with open("./cookies/weixin.json", "w") as f:
        json.dump(cookies, f)


def load_cookies():
    driver_path = "./driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://channels.weixin.qq.com/platform/post/create")

    with open("./cookies/weixin.json", "r") as f:
        cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
    # wait for the cookies to be loaded
    time.sleep(2)

    driver.get("https://channels.weixin.qq.com/platform/post/create")
    return driver


def press_publish(driver):
    """press the publish button"""

    # publish btn xpath
    publish_btn_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[10]/div[5]/span/div/button'

    # wait for the publish button to be loaded for 10 seconds
    timeout = 10
    publish_button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, publish_btn_xpath))
    )

    # click the publish button
    publish_button.click()


def upload_video_file(driver, video_path):
    """upload the video"""

    input_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div/div/div/span/div/span/input'

    # find the input element and send the video path to it
    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    input_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, input_xpath))
    )
    input_element.send_keys(video_path)


def wait_for_uploaded(driver):

    # sleep 2.5s
    time.sleep(2.5)

    # wait for video to be uploaded
    progress_element_css = "span.ant-progress-text"

    # wait untile progress element disappears
    # 等待上传完成
    while True:
        try:
            # 尝试等待元素消失，这里设置较短的等待时间
            element = WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, progress_element_css)
                )
            )
            print("上传已完成，继续!")
            break  # 元素消失，跳出循环

        except TimeoutException:
            print("上传中，继续等待...")
            continue  # 继续循环等待

    # wait 2s
    time.sleep(2)


def upload_thumbnail(driver, thumbnail_path):

    # wait for certain to disappear
    div_disable_css = "div.finder-tag-wrap.btn.disabled"

    # wait untile progress element disappears
    # 等待上传完成
    while True:
        try:
            # 尝试等待元素消失，这里设置较短的等待时间
            element = WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located((By.CSS_SELECTOR, div_disable_css))
            )
            print("封面可上传，继续!")
            break  # 元素消失，跳出循环

        except TimeoutException:
            print("封面处理中，继续等待...")
            continue  # 继续循环等待

    # 更换封面btn xpath
    change_thumbnail_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[1]/div[2]/div/div[1]/div[2]/span/div/div'

    # wait for the change thumbnail button to be loaded
    timeout = 60
    change_thumbnail_button = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, change_thumbnail_xpath))
    )

    # click the change thumbnail button
    change_thumbnail_button.click()

    # upload input xpath
    thumbnail_input_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[1]/div[2]/div/div[2]/div/div[1]/div/div[2]/div/div[1]/div[3]/div/div[1]/input'

    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    thumbnail_input = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, thumbnail_input_xpath))
    )

    # send the thumbnail path to the input element
    thumbnail_input.send_keys(thumbnail_path)

    time.sleep(5)

    #  confirm btn xpath
    confirm_btn2_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[1]/div[2]/div/div[2]/div/div[1]/div/div[3]/div/div/div[2]/button'

    # wait for confirm btn to present
    timeout = 10

    # wait for the confirm button to be clickable
    confirm_btn2 = WebDriverWait(driver, timeout).until(
        EC.element_to_be_clickable((By.XPATH, confirm_btn2_xpath))
    )

    # click the confirm button
    confirm_btn2.click()
    time.sleep(10)


def add_description(driver, description):
    # description xpath
    description_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[2]/div[2]/div/div[1]'

    # wait for the description element to be loaded for 10 seconds
    timeout = 10
    description_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, description_xpath))
    )

    # input the description char by char with random delay 0.05~0.08s
    for char_des in description:
        description_element.send_keys(char_des)
        time.sleep(random.uniform(0.05, 0.08))


def add_collection(driver, collection):
    # collection btn css selector
    col_btn_xpath = "div.post-album-wrap"

    # wait for the collection button to be loaded for 10 seconds
    timeout = 10
    col_btn = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, col_btn_xpath))
    )
    # click the collection button
    col_btn.click()

    # wait for 2s
    time.sleep(2.5)

    # 先定位合集的上层div，使用css选择器
    option_div_css = "div.common-option-list-wrap.option-list-wrap"

    upper_div = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, option_div_css))
    )

    # print length of upper_div
    # print(len(upper_div))

    # 找到所有option，使用css定位
    option_list = upper_div.find_elements(By.CSS_SELECTOR, "div.name")

    # 遍历所有option，找到对应的合集
    for id, option in enumerate(option_list):
        print(option.text, id)
        # 找到option的文本
        option_text = option.text.strip()
        # 如果文本等于合集名，点击
        if option_text == collection:
            print(f"找到合集：{collection}")
            option.click()
            break


def add_title(driver, title):
    """input title"""
    title_xpath = '//*[@id="container-wrap"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[8]/div[2]/div/div/span/input'

    # wait for the title element to be loaded for 10 seconds
    timeout = 10
    title_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, title_xpath))
    )

    # input the title
    title_element.send_keys(title)


def upload_video():
    driver = load_cookies()

    # 指定你想上传的视频文件路径
    # get absolute path of current folder
    abs_path = os.path.abspath(os.path.dirname(__file__))
    file_path = f"{abs_path}/test_videos/1.webm"
    upload_video_file(driver, file_path)

    # wait for the video to be uploaded
    wait_for_uploaded(driver)

    # 上传thumbnail
    upload_thumbnail(driver, f"{abs_path}/test_thumbnail/1.png")

    # input the description
    add_description(driver, "test description #python #刘邦 ")

    # select collection
    add_collection(driver, "test1")

    # input the title
    add_title(driver, "test title")

    # press publish
    press_publish(driver)



if __name__ == "__main__":
    # read 1st argument from command line
    if sys.argv[1] == "login":
        login_and_save_cookies()
    elif sys.argv[1] == "upload":
        upload_video()
