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
from selenium.common.exceptions import TimeoutException
import os


def login_and_save_cookies():
    # a new webdriver instance
    driver_path = "./driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://creator.douyin.com/creator-micro/content/upload")

    # wait for the user to login
    input("Press Enter after you have logged in")

    # save the cookies
    cookies = driver.get_cookies()
    with open("./cookies/douyin.json", "w") as f:
        json.dump(cookies, f)


def load_cookies():
    driver_path = "./driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://creator.douyin.com/creator-micro/content/upload")

    with open("./cookies/douyin.json", "r") as f:
        cookies = json.load(f)
        for cookie in cookies:
            driver.add_cookie(cookie)
    # wait for the cookies to be loaded
    time.sleep(2)

    driver.get("https://creator.douyin.com/creator-micro/content/upload")
    return driver


def input_video_title(driver, title):
    """input the title of the video"""

    title_xpath = (
        '//*[@id="root"]/div/div/div[2]/div[1]/div[2]/div/div/div/div[1]/div/div/input'
    )

    # 设置显式等待时间为10秒
    timeout = 10

    # wait for the element to be present
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, title_xpath))
    )

    # input the title
    element.send_keys(title)


def input_video_description(driver, description, tags):
    """input the description of the video"""

    description_xpath = (
        '//*[@id="root"]/div/div/div[2]/div[1]/div[2]/div/div/div/div[2]/div'
    )

    # 设置显式等待时间为10秒
    timeout = 10

    # wait for the element to be present
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, description_xpath))
    )

    # input the description
    element.send_keys(description)

    # input the tags
    for tag_char in tags:
        element.send_keys(tag_char)
        time.sleep(random.uniform(0.1, 0.2))


def upload_video_thumbnail(driver, thumbnail_path):
    """upload the thumbnail of the video"""

    # click the thumbnail button
    thumbnail_button_xpath = (
        '//*[@id="root"]/div/div/div[2]/div[1]/div[5]/div/div[1]/div[1]'
    )

    # click the thumbnail button
    driver.find_element(By.XPATH, thumbnail_button_xpath).click()

    ###########
    # 上传封面 xpath
    upload_thumbnail_xpath = (
        "//div[contains(@class, 'tabItem--1RmHm') and contains(text(), '上传封面')]"
    )

    # wait for the element to be present
    # 使用XPath定位具有特定类名和特定文本的<div>元素
    upload_thumbnail_button = WebDriverWait(driver, 20).until(
        EC.presence_of_element_located(
            (
                By.XPATH,
                upload_thumbnail_xpath,
            )
        )
    )

    # click the upload thumbnail button
    upload_thumbnail_button.click()
    #############

    # input xpath
    in_xpath = '//*[@id="dialog-0"]/div/div/div/div/div[2]/div[2]/input[1]'

    # 设置显式等待时间为10秒
    timeout = 10

    # 等待元素id为"my_element"的元素出现
    upload_input = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, in_xpath))
    )

    # 上传封面
    upload_input.send_keys(thumbnail_path)

    # 等待3s
    time.sleep(3)

    # 找到特定div，注，这里的div可能会有多个，第一个是需要去掉的
    elements = driver.find_elements(By.CSS_SELECTOR, "div.extractFooter--14KXV")

    # remove the first element from elements list
    elements.pop(0)

    # find all buttons under elements
    for element in elements:
        buttons = element.find_elements(By.XPATH, ".//button")
        for btn in buttons:
            if btn.text == "完成":
                btn.click()
                break


def select_video_collection(driver, collection_name):

    collection_btn_xpath = (
        '//*[@id="root"]/div/div/div[2]/div[1]/div[11]/div[2]/div[2]/div[1]/div'
    )

    # wait 10s until the element is present
    collection_btn = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, collection_btn_xpath))
    )

    # click the collection button
    collection_btn.click()

    # wait 5s
    time.sleep(3)

    # 获得全部collection的div
    # 使用CSS选择器定位元素
    all_collection = driver.find_element(By.CSS_SELECTOR, "div.semi-popover-content")

    # 在all_collection内，找所有class包含semi-select-option的div
    # 使用CSS选择器定位元素
    collections = all_collection.find_elements(
        By.CSS_SELECTOR, "div.semi-select-option.collection-option"
    )

    # 获取所有collection的text
    for c in collections:
        # print(c.text)
        if c.text == collection_name:
            print(f"find the collection: {collection_name}")
            c.click()

    # wait 2s
    time.sleep(2)


def select_no_download(driver):
    no_download_xpath = '//*[@id="root"]/div/div/div[2]/div[1]/div[15]/div/label[2]'

    # 等待上传完成
    while True:
        try:
            # 尝试等待元素消失，这里设置较短的等待时间
            element = WebDriverWait(driver, 5).until(
                EC.invisibility_of_element_located(
                    (By.CSS_SELECTOR, "span.text--2n1WY")
                )
            )
            print("Span已经消失，继续!")
            break  # 元素消失，跳出循环
        except TimeoutException:
            print("上传中，继续等待...")
            continue  # 继续循环等待

    # find and click the no download button
    # wait 10s until the element is present
    no_download_element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, no_download_xpath))
    )
    # no_download_element = driver.find_element(By.XPATH, no_download_xpath)
    no_download_element.click()
    print("no download selected!")


def publish_btn(driver):

    publish_btn_xpath = '//*[@id="root"]/div/div/div[2]/div[1]/div[17]/button[1]'
    # find and click the publish button
    publish_btn = driver.find_element(By.XPATH, publish_btn_xpath)
    publish_btn.click()

    print("published!")


def upload_video():
    driver = load_cookies()

    # input xpath
    in_xpath = '//*[@id="root"]/div/div/div[3]/div/div[1]/div/div[1]/div/label/input'

    # 设置显式等待时间为10秒
    timeout = 30

    # 等待元素id为"my_element"的元素出现
    element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, in_xpath))
    )

    # 指定你想上传的视频文件路径
    # get absolute path of current folder
    abs_path = os.path.abspath(os.path.dirname(__file__))
    file_path = f"{abs_path}/test_videos/1.webm"

    # 上传文件
    element.send_keys(file_path)

    # input the title
    input_video_title(driver, "test title")

    # input the description
    input_video_description(driver, "test description", "#python #刘邦 ")

    # upload the thumbnail
    upload_video_thumbnail(driver, f"{abs_path}/test_thumbnail/1.png")

    # wait to 10s
    time.sleep(10)

    # select collection
    select_video_collection(driver, "test1")

    # select no download
    select_no_download(driver)

    # publish
    publish_btn(driver)

    # 等待上传完成
    # time.sleep(1000)


if __name__ == "__main__":

    # read parameters from the command line
    # get the first parameter
    action = sys.argv[1]
    if action == "login":
        login_and_save_cookies()
    elif action == "upload":
        upload_video()
