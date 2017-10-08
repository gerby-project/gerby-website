from sqlite3 import connect
from selenium import webdriver
from time import sleep

database = "../stacks.sqlite"
url = "http://localhost:5000"
setup_done_flag = """
window.done = false;
MathJax.Hub.Queue(function() { window.done = true; })
"""
find_tex_errors = """
if(window.done) {
    allJax = MathJax.Hub.getAllJax();
    errors = [];
    for (i = 0; i < allJax.length; i++) {
        if(allJax[i].texError) {
            errors.push(allJax[i].originalText);
        }
    }
    return errors;
} else {
    return -1;
}
"""

def get_tex_errors_on_tag(tag,browser=None):
    if browser is None:
        browser = webdriver.Firefox()
    browser.get("{0}/tag/{1}".format(url,tag))
    browser.execute_script(setup_done_flag)
    errors = browser.execute_script(find_tex_errors)
    while errors == -1:
        sleep(1)
        errors = browser.execute_script(find_tex_errors)
    if browser is None:
        browser.quit()
    return errors

conn = connect(database)
c = conn.cursor()
c.execute('SELECT tag FROM tag WHERE type IS "section";')
tags = c.fetchall()
conn.close()
print("There are {0} sections.".format(len(tags)))

browser = webdriver.Firefox()
sections_done = 0
for tag in tags:
    errors = get_tex_errors_on_tag(tag[0],browser=browser)
    if errors:
        print("There are TeX errors at Tag {0}:".format(tag[0]))
        for error in errors:
            print(error)
    sections_done += 1
    if sections_done % 100 == 0:
        print("--- Done testing {0} sections.".format(sections_done))

browser.quit()
