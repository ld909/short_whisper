import random
import time
from selenium import webdriver
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys


def login_and_save_cookies():
    # a new webdriver instance
    driver_path = "/Users/donghaoliu/doc/short_whisper/short/driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://cp.kuaishou.com/profile")

    # wait for the user to login
    input("登录完成按任意键继续")

    # save the cookies
    cookies = driver.get_cookies()
    with open(
        "/Users/donghaoliu/doc/short_whisper/short/cookies/kuaishou.json", "w"
    ) as f:
        json.dump(cookies, f)


def load_cookies():
    driver_path = "/Users/donghaoliu/doc/short_whisper/short/driver/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://cp.kuaishou.com/profile")

    with open(
        "/Users/donghaoliu/doc/short_whisper/short/cookies/kuaishou.json", "r"
    ) as f:
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
    no_download_xpath = '//*[@id="rc-tabs-0-panel-1"]/div/div[4]/div/div[4]/div[2]/div[4]/div/label[2]/span[1]/input'

    # wait for the input element to be loaded for 10 seconds, if not loaded, just continue the next step
    timeout = 10
    try:
        no_download_element = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.XPATH, no_download_xpath))
        )
        no_download_element.click()
        print("点击不允许下载...")
    except:
        print('没有找到"不允许下载"的checkbox...')
        pass


def confirm_publish_video(driver):
    """press the publish button"""

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

    # publish button css div.XwacrNGK2pY-
    publish_button_css = "div.XwacrNGK2pY-"
    div_element = driver.find_element(By.CSS_SELECTOR, publish_button_css)
    # find all button elements
    spans = div_element.find_elements(By.TAG_NAME, "span")
    # click the button with text "发布"
    for span in spans:
        if span.text == "发布":
            span.click()
            print("点击发布按钮...")

    # wait 2s
    time.sleep(2)

    # 确认发布
    confirm_btn_full_xpath = (
        "/html/body/div[2]/div[4]/div/div[2]/div/div[2]/div/div/div[2]/button[2]/span"
    )
    confirm_btn_element = driver.find_element(By.XPATH, confirm_btn_full_xpath)
    confirm_btn_element.click()
    time.sleep(2)
    print("确认发布...")


def set_timedate(driver, time_str):
    """设置定时发布时间"""

    # 点击定时发布
    father_css = "div.FEOCM-Tkqec-"
    father_element = driver.find_element(By.CSS_SELECTOR, father_css)

    # 找到father element下的所有label
    labels = father_element.find_elements(By.TAG_NAME, "label")

    # 点击第2个label
    labels[1].click()
    print("点击定时发布")

    # 输入时间
    input_father_css = "div.KEH-2Slzocg-"
    # 找到father element
    input_father_element = driver.find_element(By.CSS_SELECTOR, input_father_css)

    # 找到input element
    input_element = input_father_element.find_elements(By.TAG_NAME, "input")
    input_element = input_element[0]
    time.sleep(1)
    input_element.send_keys(time_str)
    time.sleep(1.5)
    # press enter key
    input_element.send_keys(Keys.ENTER)
    print(f"快手短视频，设定发布时间:{time_str}完成...")


def publish_kuaishou_video(
    mp4_path, thumbnail_path, title_and_description_str, time_str
):
    # load the cookies
    driver = load_cookies()

    time.sleep(3.5)
    # upload video
    video_upload(driver, mp4_path)

    # upload thumbnail
    upload_video_thumbnail(driver, thumbnail_path)

    # wait 5s
    time.sleep(5)
    # input the title and description
    # title_and_description = "test title and description #刘邦 #python "
    input_title_and_description(driver, title_and_description_str)

    # check the no download checkbox
    no_download_check(driver)

    set_timedate(driver, time_str)

    # confirm publish video
    confirm_publish_video(driver)

    time.sleep(5)

    # close the chrome driver
    driver.quit()


if __name__ == "__main__":
    login_and_save_cookies()
# publish_video()
