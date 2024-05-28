import pyautogui
from selenium.webdriver.common.keys import Keys
from datetime import datetime, timedelta
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
from selenium.webdriver.common.action_chains import ActionChains


def login_and_save_cookies(topic):
    # a new webdriver instance
    driver_path = "/home/dhl/Downloads/chromedriver-linux64/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://channels.weixin.qq.com/platform/post/create")

    # wait for the user to login
    input("登录完成按任意键继续")

    # save the cookies
    cookies = driver.get_cookies()
    with open(f"./short/{topic}/weixin.json", "w") as f:
        json.dump(cookies, f)


def load_cookies(topic):
    driver_path = "/home/dhl/Downloads/chromedriver-linux64/chromedriver"
    service = Service(executable_path=driver_path)

    driver = webdriver.Chrome(service=service)

    # open the login page
    driver.get("https://channels.weixin.qq.com/platform/post/create")

    with open(f"./short/{topic}/weixin.json", "r") as f:
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

    time.sleep(2)

    # 平铺展示btn xpath
    exten_thumbnail_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[1]/div[2]/div/div[2]/div/div[1]/div/div[2]/div/div[2]/div[2]/div[1]/div[2]/div[2]/div"
    # find the extend thumbnail button and click it
    extend_thumbnail_button = driver.find_element(By.XPATH, exten_thumbnail_xpath)
    extend_thumbnail_button.click()

    time.sleep(1.5)

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
    time.sleep(2)


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
    title_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[8]/div[2]/div/div/span/input"

    # wait for the title element to be loaded for 10 seconds
    timeout = 10
    title_element = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, title_xpath))
    )

    # input the title
    title = title.replace("!", "")
    title = title.replace("！", "")
    title_element.send_keys(title)


def set_time(time_str):
    print("weixin设定的发布时间：", time_str)
    # wait for use to set time press enter to continue
    print("请设定发布时间，按Enter键继续...")
    input()
    print("程序继续执行")


def set_time_program(driver, time_str):

    # get month, date, hour by splitting the time_str:2024-05-22-21-00
    print("weixin设定的发布时间：", time_str)

    time_year_month, hour_minute = time_str.split(" ")
    time_list = time_year_month.split("-")

    target_year = time_list[0]
    target_month = time_list[1]
    target_day = time_list[2]
    target_hour, target_minute = hour_minute.split(":")

    # 点击设定时间按钮
    set_time_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[7]/div/div[2]/div/label[2]/i"
    timeout = 10
    set_time_btn = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, set_time_xpath))
    )
    set_time_btn.click()

    # click time date input
    time_date_area_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[7]/div[2]/div[2]/dl/dt/span[1]/div/span/input"

    # wait for the title element to be loaded for 10 seconds
    timedate_ele = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, time_date_area_xpath))
    )
    timedate_ele.click()

    # default year
    year_full_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[7]/div[2]/div[2]/dl/dd/div/div[1]/span[1]"

    # wait for the year text to be loaded
    year_full_ele = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, year_full_xpath))
    )
    # get the year text
    defult_year = year_full_ele.text.strip()
    if defult_year != target_year + "年":
        print(f"需要重新选择年")
        # click the year
        year_full_ele.click()
        # select the year
        # year table class=weui-desktop-picker__table, locate it by css
        year_table_css = "div.weui-desktop-picker__panel__bd"

        # wait for the year table to be loaded
        year_table = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, year_table_css))
        )

        # find all the a tags in the year table, note that a tags are not direct children of the table
        year_list = year_table.find_elements(By.CSS_SELECTOR, "a")

        # find the target year
        for year_ele in year_list:
            cur_year_text = year_ele.text.strip()
            if cur_year_text == target_year:
                print(f"找到目标年份：{target_year}")
                year_ele.click()
                break

    # 月份
    month_full_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[7]/div[2]/div[2]/dl/dd/div/div[1]/span[2]"
    # month_full_xpath text
    month_full_ele = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, month_full_xpath))
    )
    # get the month text
    defult_month = month_full_ele.text.strip()
    if len(target_month) == 1:
        target_month_new = "0" + target_month
    else:
        target_month_new = target_month
    if defult_month != target_month_new + "月":
        print(f"需要重新选择月")
        # click the month
        month_full_ele.click()
        # select the month
        # month table class=weui-desktop-picker__table, locate it by css
        month_picker_css = "div.weui-desktop-picker__panel__bd"

        # wait for the month table to be loaded
        month_table = WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, month_picker_css))
        )

        # find all the a tags in the month table, note that a tags are not direct children of the table
        month_list = month_table.find_elements(By.CSS_SELECTOR, "a")

        # find the target month
        for month_ele in month_list:
            cur_month_text = month_ele.text.strip()
            if cur_month_text == target_month:
                print(f"找到目标月份：{target_month}")
                month_ele.click()
                break

    time.sleep(1)

    # 日
    # date_picker_css = "div.weui-desktop-picker__panel__bd"
    all_dates = driver.find_elements(
        By.CSS_SELECTOR, "div.weui-desktop-picker__panel__bd td a"
    )
    for date in all_dates:
        print("当前date:", date.text.strip())
        date_text = date.text.strip()
        if date_text == target_day:
            print(f"找到目标日期：{date_text}")
            # double click the date
            # get date x, y
            date.click()
            break

    time.sleep(100000)

    # 时+分
    # 点击i元素，这个元素是class为weui-desktop-icon__time，用css定位
    hour_minute_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[7]/div[2]/div[2]/dl/dd/div/div[3]/dl/dt/span/div/span/input"
    hour_minute_ele = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, hour_minute_xpath))
    )
    hour_minute_ele.click()

    # ol的class定位hour picker
    hour_picker_css = (
        "ol.weui-desktop-picker__time__panel.weui-desktop-picker__time__hour"
    )
    hour_picker = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, hour_picker_css))
    )

    # get all li elements in the hour picker
    hour_list = hour_picker.find_elements(By.CSS_SELECTOR, "li")

    # find the target hour
    if len(target_hour) == 1:
        target_hour_new = "0" + target_hour
    else:
        target_hour_new = target_hour
    for hour_ele in hour_list:
        cur_hour_text = hour_ele.text.strip()
        if cur_hour_text == target_hour_new:
            print(f"找到目标小时：{target_hour}")
            hour_ele.click()
            break

    # get minute ol element by weui-desktop-picker__time__panel weui-desktop-picker__time__minute class name
    minute_picker_css = (
        "ol.weui-desktop-picker__time__panel.weui-desktop-picker__time__minute"
    )
    minute_picker = WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, minute_picker_css))
    )
    # 只选择整点发布
    all_minutes = minute_picker.find_elements(By.CSS_SELECTOR, "li")
    for minute in all_minutes:
        minute_text = minute.text.strip()
        if minute_text == "00":
            print(f"找到目标分钟：{target_minute}")
            minute.click()
            break

    # # 再次点击“定时”
    # set_time_full_xpath = "/html/body/div[1]/div/div[2]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[2]/div[6]/div[1]/div[2]/div/label[2]"
    # # wait for the title element to be loaded for 10 seconds
    # set_time_full_ele = WebDriverWait(driver, timeout).until(
    #     EC.presence_of_element_located((By.XPATH, set_time_full_xpath))
    # )
    # set_time_full_ele.click()

    # 使用 JavaScript 在网页的空白处点击一次
    driver.execute_script("document.body.click();")


def upload_weixin_video(
    mp4_path, thumbnail_path, title, title_and_description, time_str, topic
):
    driver = load_cookies(topic)

    # 指定你想上传的视频
    upload_video_file(driver, mp4_path)

    # wait for the video to be uploaded
    wait_for_uploaded(driver)

    # 上传thumbnail
    upload_thumbnail(driver, thumbnail_path)

    # input the description
    add_description(driver, title_and_description)

    # convert time_str to timedelta object,2024-05-14 06:00 using format "%Y-%m-%d %H:%M"
    time_str_obj = datetime.strptime(time_str, "%Y-%m-%d %H:%M")
    # if time_str_obj is less than current time, set time to 1 hour later
    if time_str_obj < datetime.now():
        time_str = (datetime.now() + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M")
        print(f"微信时间设置错误，新设定为1小时后发布：{time_str}")

    # 使用pyautogui按下page down键，滚动到页面底部
    time.sleep(0.5)
    pyautogui.press("pagedown")
    time.sleep(1)
    print("滚动到页面底部...")

    set_time_program(driver=driver, time_str=time_str)

    # input the title
    if len(title) <= 6:
        title += "     "
    add_title(driver, title)

    time.sleep(1)

    # press publish
    press_publish(driver)

    time.sleep(10)

    # close the chrome driver
    driver.quit()


if __name__ == "__main__":
    # read 1st argument from command line
    if sys.argv[1] == "login":
        topic = sys.argv[2]
        login_and_save_cookies(topic)
# elif sys.argv[1] == "upload":
#     upload_video()
