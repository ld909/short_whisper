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


def login_and_save_cookies():
    # a new webdriver instance
    driver_path = "./driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://cp.kuaishou.com/profile")

    # wait for the user to login
    input("登录完成按任意键继续")

    # save the cookies
    cookies = driver.get_cookies()
    with open("./cookies/kuaishou.json", "w") as f:
        json.dump(cookies, f)


def load_cookies():
    driver_path = "./driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://cp.kuaishou.com/profile")

    with open("./cookies/kuaishou.json", "r") as f:
        cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
    # wait for the cookies to be loaded
    time.sleep(2)

    driver.get("https://cp.kuaishou.com/article/publish/video")
    return driver


def video_upload(driver, video_path):
    """upload the video"""

    input_xpath = '//*[@id="rc-tabs-0-panel-1"]/div/input'

    # find the input element and send the video path to it
    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    input_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, input_xpath))
    )
    input_element.send_keys(video_path)


def upload_video_thumbnail(driver, thumbnail_path):
    """upload the thumbnail of the video"""

    input_xpath = '//*[@id="rc-tabs-7-panel-1"]/div/div[3]/button'

    # find the input element and send the thumbnail path to it
    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    bianji_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, input_xpath))
    )
    # input_element.send_keys(thumbnail_path)

    # click bianji
    bianji_element.click()

    # 上传button xpath
    upload_xpath = '//*[@id="rc-tabs-2-tab-2"]'

    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    upload_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, upload_xpath))
    )
    upload_element.click()

    # upload input xpath
    upload_input_xpath = '//*[@id="rc-tabs-2-panel-2"]/input'

    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    upload_input_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, upload_input_xpath))
    )
    upload_input_element.send_keys(thumbnail_path)

    # 确认 button xpath
    confirm_xpath = '//*[@id="rc-tabs-0-panel-1"]/div/div[1]/div[2]/div[2]/button[1]'
    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    confirm_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, confirm_xpath))
    )
    confirm_element.click()


def input_title_and_description(driver, title_and_description):
    """input the title and description of the video"""

    input_area_xpath = "div.clGhv3UpdEo-"

    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    input_area_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, input_area_xpath))
    )

    # input char by char, each char has a random delay 0.1s~0.2s
    for single_char in title_and_description:
        input_area_element.send_keys(single_char)
        time.sleep(random.uniform(0.05, 0.08))


def no_download_check(driver):
    """check the no download checkbox"""
    no_download_xpath = (
        '//*[@id="rc-tabs-0-panel-1"]/div/div[4]/div/div[4]/div[2]/div[3]/div/label[2]'
    )

    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    no_download_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, no_download_xpath))
    )
    no_download_element.click()


def confirm_publish_video(driver):
    """press the publish button"""
    publish_btn_xpath = (
        '//*[@id="rc-tabs-0-panel-1"]/div/div[4]/div/div[4]/div[2]/div[8]/button[1]'
    )

    # wait for the input element to be loaded for 10 seconds
    timeout = 10
    publish_btn_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, publish_btn_xpath))
    )

    # get upload progress under span element
    progress_xpath = "span.DqNkLCyIyfQ-"
    cur_text = "0"

    while cur_text != "上传成功":
        progress_element = driver.find_element(By.CSS_SELECTOR, progress_xpath)
        cur_text = progress_element.text
        cur_text = cur_text.strip()
        print(f"当前状态:{cur_text}...")
        time.sleep(2)

    print("上传成功....")

    # wait 2s
    time.sleep(2)

    publish_btn_element.click()


def publish_video():

    driver = load_cookies()

    # 指定你想上传的视频文件路径
    # get absolute path of current folder
    abs_path = os.path.abspath(os.path.dirname(__file__))
    file_path = f"{abs_path}/test_videos/1.webm"

    # upload video
    video_upload(driver, file_path)

    # upload thumbnail
    thumbnail_path = f"{abs_path}/test_thumbnail/1.png"
    upload_video_thumbnail(driver, thumbnail_path)

    # wait 5s
    time.sleep(5)
    # input the title and description
    title_and_description = "test title and description #刘邦 #python "
    input_title_and_description(driver, title_and_description)

    # check the no download checkbox
    no_download_check(driver)

    # confirm publish video
    confirm_publish_video(driver)


if __name__ == "__main__":
    # login_and_save_cookies()
    publish_video()
