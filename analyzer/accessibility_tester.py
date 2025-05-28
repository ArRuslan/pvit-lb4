"""This module includes the accessibility tester and all its functionality"""
from typing import TypedDict

from bs4 import BeautifulSoup, Comment, Doctype
from selenium import webdriver
from selenium.common.exceptions import MoveTargetOutOfBoundsException, NoSuchElementException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions

SCORE_MULTIPLIERS = {
    "doc_language": .9,
    "alt_texts": .9,
    "input_labels": .9,
    "empty_buttons": .9,
    "empty_links": .9,
    "color_contrast": .3,
}

class CounterDict(TypedDict):
    doc_language: int
    alt_texts: int
    input_labels: int
    empty_buttons: int
    empty_links: int
    color_contrast: int


class AccessibilityTester:
    """
    An instance of the Accessibility Tester

    Attributes
    ----------
    url : str
        The url of the page that should be tested
    browser_height : int
        The height of the browser window
    browser_width : int
        The width of the browser window
    """
    def __init__(self, url: str, browser_height: int = 720, browser_width: int = 1280):
        self.url = url
        self.browser_height = browser_height
        self.browser_width = browser_width
        self.driver = None
        self.page = None
        self.correct: CounterDict = {
            "doc_language": 0,
            "alt_texts": 0,
            "input_labels": 0,
            "empty_buttons": 0,
            "empty_links": 0,
            "color_contrast": 0,
        }
        self.wrong: CounterDict = {
            "doc_language": 0,
            "alt_texts": 0,
            "input_labels": 0,
            "empty_buttons": 0,
            "empty_links": 0,
            "color_contrast": 0,
        }

        self.visited_links = []

    def start_driver(self):
        options = FirefoxOptions()
        options.headless = True
        options.add_argument("--headless")
        options.add_argument("--log-level=3")

        self.driver = webdriver.Firefox(options=options)

        self.driver.set_window_size(self.browser_width, self.browser_height)
        self.driver.get(self.url)
        self.page = BeautifulSoup(self.driver.page_source, "html.parser")

    def test_page(self):
        """This function executes the tests for the current page. If tests for subpages are enabled, it will also test all subpages"""
        self.page = BeautifulSoup(self.driver.page_source, "html.parser")
        self.check_doc_language()
        self.check_alt_texts()
        self.check_input_labels()
        self.check_buttons()
        self.check_links()
        self.check_color_contrast()

    def check_doc_language(self):
        """This function checks if the doc language is set (3.1.1 H57)"""
        # check if language attribute exists and is not empty
        lang_attr = self.page.find("html").get_attribute_list("lang")[0]
        if not lang_attr is None and not lang_attr == "":
            print("  Document language is set")
            self.correct["doc_language"] += 1
        elif not lang_attr is None:
            print("x Document language is empty")
            self.wrong["doc_language"] += 1
        else:
            print("x Document language is missing")
            self.wrong["doc_language"] += 1

    def error_if_visible(self, xpath: str, text: str) -> bool:
        try:
            el = self.driver.find_element(By.XPATH, xpath)
            ActionChains(self.driver).move_to_element(el).perform()
        except (MoveTargetOutOfBoundsException, NoSuchElementException):
            print(f"  {text}, but element is not visible", xpath)
            return False

        if el.is_displayed():
            print(f"x {text}", xpath)
            return False

        return True

    def check_alt_texts(self):
        """This function checks if all images on the page have an alternative text (1.1.1 H37)"""
        # get all img elements
        img_elements = self.page.find_all("img")
        for img_element in img_elements:
            # check if img element has an alternative text that is not empty
            alt_text = img_element.get_attribute_list('alt')
            if not alt_text:
                el_xpath = xpath_soup(img_element)
                if not self.error_if_visible(el_xpath, "Alt text is missing"):
                    self.wrong["alt_texts"] += 1
                continue

            alt_text = alt_text[0]
            if not alt_text is None and not alt_text == "":
                print("  Alt text is correct", xpath_soup(img_element))
                self.correct["alt_texts"] += 1
            elif not alt_text is None:
                el_xpath = xpath_soup(img_element)
                if not self.error_if_visible(el_xpath, "Alt text is empty"):
                    self.wrong["alt_texts"] += 1
            else:
                el_xpath = xpath_soup(img_element)
                if not self.error_if_visible(el_xpath, "Alt text is missing"):
                    self.wrong["alt_texts"] += 1

    def check_input_labels(self):
        """This function checks if all input elements on the page have some form of label (1.3.1 H44 & ARIA16)"""
        # get all input and label elements
        input_elements = self.page.find_all("input")
        label_elements = self.page.find_all("label")
        for input_element in input_elements:
            # exclude input element of type hidden, submit, reset and button
            if ("type" in input_element.attrs and not input_element['type'] == "hidden" and not input_element['type'] == "submit" \
                    and not input_element['type'] == "reset" and not input_element['type'] == "button") or "type" not in input_element.attrs:
                # check if input is of type image and has a alt text that is not empty
                if "type" in input_element.attrs and input_element['type'] == "image" and "alt" in input_element.attrs \
                        and not input_element['alt'] == "":
                    print("  Input of type image labelled with alt text", xpath_soup(input_element))
                    self.correct["input_labels"] += 1
                # check if input element uses aria-label
                elif "aria-label" in input_element.attrs and not input_element['aria-label'] == "":
                    print("  Input labelled with aria-label attribute", xpath_soup(input_element))
                    self.correct["input_labels"] += 1
                # check if input element uses aria-labelledby
                elif "aria-labelledby" in input_element.attrs and not input_element['aria-labelledby'] == "":
                    label_element = self.page.find(id=input_element['aria-labelledby'])
                    if not label_element is None:
                        texts_in_label_element = label_element.findAll(text=True)
                        if not texts_in_label_element == []:
                            print("  Input labelled with aria-labelledby attribute", xpath_soup(input_element))
                            self.correct["input_labels"] += 1
                        else:
                            print("x Input labelled with aria-labelledby attribute, but related label has no text", xpath_soup(input_element))
                            self.wrong["input_labels"] += 1
                    else:
                        print("x Input labelled with aria-labelledby attribute, but related label does not exist", xpath_soup(input_element))
                        self.wrong["input_labels"] += 1
                else:
                    # check if input element has a corresponding label element
                    label_correct = False
                    for label_element in label_elements:
                        # check if "for" attribute of label element is identical to "id" of input element
                        if "for" in label_element.attrs and "id" in input_element.attrs and label_element['for'] == input_element['id']:
                            label_correct = True
                    if label_correct:
                        print("  Input labelled with label element", xpath_soup(input_element))
                        self.correct["input_labels"] += 1
                    else:
                        print("x Input not labelled at all", xpath_soup(input_element))
                        self.wrong["input_labels"] += 1

    def check_buttons(self):
        """This function checks if all buttons and input elements of the types submit, button and reset have some form of content (1.1.1 & 2.4.4)"""
        # get all buttons and input elements of the types submit, button and reset
        input_elements = self.page.find_all("input", type=["submit", "button", "reset"])
        button_elements = self.page.find_all("button")

        for input_element in input_elements:
            # check if input element has a value attribute that is not empty
            if "value" in input_element.attrs and not input_element['value'] == "":
                print("  Button has content", xpath_soup(input_element))
                self.correct["empty_buttons"] += 1
            else:
                print("x Button is empty", xpath_soup(input_element))
                self.wrong["empty_buttons"] += 1

        for button_element in button_elements:
            # check if the button has content or a title
            texts = button_element.findAll(text=True)
            if not texts == [] or ("title" in button_element.attrs and not button_element["title"] == ""):
                print("  Button has content", xpath_soup(button_element))
                self.correct["empty_buttons"] += 1
            else:
                print("x Button is empty", xpath_soup(button_element))
                self.wrong["empty_buttons"] += 1

    def check_links(self):
        """This function checks if all links on the page have some form of content (2.4.4 G91 & H30)"""
        # get all a elements
        link_elements = self.page.find_all("a")
        for link_element in link_elements:
            # check if link has content
            texts_in_link_element = link_element.findAll(text=True)
            img_elements = link_element.findChildren("img", recursive=False)
            all_alt_texts_set = True
            for img_element in img_elements:
                alt_text = img_element.get_attribute_list('alt')[0]
                if alt_text is None or alt_text == "":
                    all_alt_texts_set = False
            if not texts_in_link_element == [] or (not img_elements == [] and all_alt_texts_set):
                print("  Link has content", xpath_soup(link_element))
                self.correct["empty_links"] += 1
            else:
                print("x Link is empty", xpath_soup(link_element))
                self.wrong["empty_links"] += 1

    def check_color_contrast(self):
        """This function checks if all texts on the page have high enough contrast to the color of the background (1.4.3 G18 & G145 (& 148))"""
        # exclude script, style, title and empty elements as well as doctype and comments
        texts_on_page = extract_texts(self.page)
        input_elements = self.page.find_all("input")
        elements_with_text = texts_on_page + input_elements
        for text in elements_with_text:
            selenium_element = self.driver.find_element(by="xpath", value=xpath_soup(text))
            # exclude invisible texts
            element_visible = selenium_element.value_of_css_property('display')
            if not element_visible == "none" and (not text.name == "input" or (text.name == "input" \
                    and "type" in text.attrs and not text['type'] == "hidden")):
                text_color = convert_to_rgba_value(selenium_element.value_of_css_property('color'))
                background_color = get_background_color(self.driver, text)

                # calculate contrast between text color and background color
                contrast = get_contrast_ratio(eval(text_color[4:]), eval(background_color[4:]))

                # get font size and font weight
                font_size = selenium_element.value_of_css_property('font-size')
                font_weight = selenium_element.value_of_css_property('font-weight')

                if not font_size is None and font_size.__contains__("px") and \
                        (int(''.join(filter(str.isdigit, font_size))) >= 18 or ((font_weight == "bold" or font_weight == "700" \
                        or font_weight == "800" or font_weight == "900" or text.name == "strong") \
                        and int(''.join(filter(str.isdigit, font_size))) >= 14)):
                    if contrast >= 3:
                        print("  Contrast meets minimum requirements", xpath_soup(text), text_color, background_color)
                        self.correct["color_contrast"] += 1
                    else:
                        print("x Contrast does not meet minimum requirements", xpath_soup(text), text_color, background_color)
                        self.wrong["color_contrast"] += 1
                else:
                    if contrast >= 4.5:
                        print("  Contrast meets minimum requirements", xpath_soup(text), text_color, background_color)
                        self.correct["color_contrast"] += 1
                    else:
                        print("x Contrast does not meet minimum requirements", xpath_soup(text), text_color, background_color)
                        self.wrong["color_contrast"] += 1

    @staticmethod
    def calculate_result(correct: dict, wrong: dict) -> float:
        """This function calculates the result of the test and prints it to the console"""
        # calculate correct and false implementations
        total: dict = {}
        for key, count in correct.items():
            if key not in total:
                total[key] = 0
            total[key] += count
        for key, count in wrong.items():
            if key not in total:
                total[key] = 0
            total[key] += count

        scores = {}
        for key, total_score in total.items():
            if not total_score:
                continue
            scores[key] = correct.get(key, 0) / total_score

        corrected_scores = {}
        for key, score in scores.items():
            corrected_scores[key] = score * SCORE_MULTIPLIERS[key]

        corrected_score = sum(scores.values()) / len(scores)
        corrected_score /= sum(SCORE_MULTIPLIERS.values()) / len(SCORE_MULTIPLIERS)
        corrected_score = max(1., min(0., corrected_score))

        return corrected_score


# src: https://gist.github.com/ergoithz/6cf043e3fdedd1b94fcf
def xpath_soup(element):
    # pylint: disable=consider-using-f-string
    """This function calculates the xpath of an element"""
    if element is None:
        return '/html'
    components = []
    child = element if element.name else element.parent
    for parent in child.parents:  # type: bs4.element.Tag
        siblings = parent.find_all(child.name, recursive=False)
        components.append(
            child.name if 1 == len(siblings) else '%s[%d]' % (
                child.name,
                next(i for i, s in enumerate(siblings, 1) if s is child)
                )
            )
        child = parent
    components.reverse()
    if not components:
        return '/html'
    return '/%s' % '/'.join(components)

def extract_texts(soup):
    """This function extracts all texts from a page"""
    soup2 = soup

    # remove script, style and title elements
    for invisible_element in soup2(["script", "style", "title", "noscript"]):
        invisible_element.extract()

    # remove comments
    comments = soup2.findAll(text=lambda text:isinstance(text, Comment))
    for comment in comments:
        comment.extract()

    # remove doctype
    doctype = soup2.find(text=lambda text:isinstance(text, Doctype))
    if not doctype is None:
        doctype.extract()

    # get all elements with text
    texts = []
    texts_on_page = soup2.findAll(text=True)
    for text in texts_on_page:
        if not text.strip() == "" and not text == "\n":
            texts.append(text.parent)

    return texts

def get_background_color(driver, text):
    """This function returns the background color of a given text"""
    if text is None:
        return "rgba(255,255,255,1)"

    selenium_element = driver.find_element(by="xpath", value=xpath_soup(text))
    background_color = convert_to_rgba_value(selenium_element.value_of_css_property('background-color'))

    if eval(background_color[4:])[3] == 0:
        return get_background_color(driver, text.parent)

    return background_color

def convert_to_rgba_value(color):
    """This function converts a color value to the rgba format"""
    if color[:4] != "rgba":
        rgba_tuple = eval(color[3:]) + (1,)
        color = "rgba" + str(rgba_tuple)

    return color

def get_contrast_ratio(text_color, background_color):
    """This function calculates the contrast ratio between text color and background color"""
    # preparing the RGB values
    r_text = convert_rgb_8bit_value(text_color[0])
    g_text = convert_rgb_8bit_value(text_color[1])
    b_text = convert_rgb_8bit_value(text_color[2])
    r_background = convert_rgb_8bit_value(background_color[0])
    g_background = convert_rgb_8bit_value(background_color[1])
    b_background = convert_rgb_8bit_value(background_color[2])

    # calculating the relative luminance
    luminance_text = 0.2126 * r_text + 0.7152 * g_text + 0.0722 * b_text
    luminance_background = 0.2126 * r_background + 0.7152 * g_background + 0.0722 * b_background

    # check if luminance_text or luminance_background is lighter
    if luminance_text > luminance_background:
        # calculating contrast ration when luminance_text is the relative luminance of the lighter colour
        contrast_ratio = (luminance_text + 0.05) / (luminance_background + 0.05)
    else:
        # calculating contrast ration when luminance_background is the relative luminance of the lighter colour
        contrast_ratio = (luminance_background + 0.05) / (luminance_text + 0.05)

    return contrast_ratio

def convert_rgb_8bit_value(single_rgb_8bit_value):
    """This function converts an rgb value to the needed format"""
    # dividing the 8-bit value through 255
    srgb = single_rgb_8bit_value / 255

    # check if the srgb value is lower than or equal to 0.03928
    if srgb <= 0.03928:
        return srgb / 12.92

    return ((srgb + 0.055) / 1.055) ** 2.4
