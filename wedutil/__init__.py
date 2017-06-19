"""
This module provides functions to check on the status of a wed
editor located at ``window.wed_editor``. Reading private variables
directly is fair game here.

"""

import os
from distutils.version import StrictVersion

import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
import selenium

if not os.environ.get("WEDUTIL_SKIP_OSX_CHECK", False) \
   and StrictVersion(selenium.__version__) > StrictVersion("2.53.2"):
    # This check is performed by running a test that uses the cut()
    # function below. Run the test without the osx specific code. If
    # the test passes, then the rigmarole is no longer needed.
    raise Exception("check whether you still need the cut "
                    "rigmarole on OS X in this version ({0}) of Selenium"
                    .format(selenium.__version__))


def is_caret_in(util, element):
    """
    Tests whether the caret is in the element.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    :param element: The DOM element.
    :type element: This can be a jQuery selector or
          :class:`selenium.webdriver.remote.webelement.WebElement`
    """
    driver = util.driver

    return driver.execute_script("""
    var $ = jQuery;
    var element = arguments[0];
    var caret = wed_editor.caretManager.caret;
    return caret && $(caret.node).closest($(element)).length > 0;
    """, element)


def wait_for_caret_to_be_in(util, element):
    """
    Waits for the caret to be in an element.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    :param element: The DOM element.
    :type element: This can be a jQuery selector or
          :class:`selenium.webdriver.remote.webelement.WebElement`
    """

    util.wait(lambda driver: is_caret_in(util, element))


def click_until_caret_in(util, element, target=None):
    """
    Clicks on an element until the caret is in it. This is needed due
    to the asynchronous nature of wed. Between the time Selenium gets
    the coordinates of an element and the time it performs the click,
    there seem to be an opportunity for the JavaScript code of wed to
    make changes to the UI that can push the element away from the
    coordinates that Selenium got. (Especially the case on FF.)

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    :param element: The DOM element on which to click.
    :type element:
          :class:`selenium.webdriver.remote.webelement.WebElement`
    :param target: The DOM element in which the caret should be. If
                   not specified, it is assumed to be the same as
                   ``element``.
    :type target:
          :class:`selenium.webdriver.remote.webelement.WebElement`
    """

    if target is None:
        target = element

    while True:
        ActionChains(util.driver) \
            .click(element) \
            .perform()

        if is_caret_in(util, target):
            break


def caret_screen_pos(driver):
    """
    Gets the ``x, y`` position of the caret relative to the
    screen.

    :param driver: The Selenium driver to operate on.
    :returns: The position.
    :rtype: ``{"left": x, "top": y}`` where ``x`` and ``y`` are
            the coordinates.
    """
    pos = driver.execute_script("""
    var pos = wed_editor._caretMark.getBoundingClientRect();
    return { left: pos.left, top: pos.top };
    """)

    # ChromeDriver chokes on float values.
    pos["left"] = int(pos["left"])
    pos["top"] = int(pos["top"])
    return pos


def caret_selection_pos(driver):
    """
    This returns the caret position **for the sake of subsequently
    using this position to select text.**

    Gets the ``x, y`` position of the caret relative to the
    screen. The ``y`` coordinate is set to the middle of the caret's
    height to avoid boundary conditions.

    :param driver: The Selenium driver to operate on.
    :returns: The position.
    :rtype: ``{"left": x, "top": y}`` where ``x`` and ``y`` are
            the coordinates.
    """
    pos = driver.execute_script("""
    var pos = wed_editor._caretMark.getBoundingClientRect();
    return { left: pos.left, top: pos.top + pos.height / 2};
    """)

    # ChromeDriver chokes on float values.
    pos["left"] = round(pos["left"])
    pos["top"] = round(pos["top"])
    return pos


def point_in_selection(driver):
    """
    This method will get the coordinates of a point inside the
    selection. It is limited in that the start of the current range
    must be in a text node and start before the end of text in the
    node.

    :returns: A point inside the current selection. With the keys
              ``"x"`` and ``"y"`` set to the coordinates of the
              point. The coordinates are relative to the screen.
    :rtype: class:`dict`
    """
    return driver.execute_script("""
    var sel = wed_editor.my_window.getSelection();
    if (sel.rangeCount === 0)
        return undefined;

    var range = sel.getRangeAt(0).cloneRange();
    if (range.startContainer.nodeType !== Node.TEXT_NODE)
        return undefined;

    if (range.startOffset >= range.startContainer.nodeValue.length)
        return undefined;

    range.collapse(true);
    range.setEnd(range.startContainer, range.startOffset + 1);
    var rect = range.getBoundingClientRect();
    // Return a position just inside the rect.
    var pos = {x: rect.left + 1, y: rect.top + 1};
    return pos;
    """)


def set_window_size(util, width, height):
    """
    Sets the window size and then waits until the wed editor has
    changed size too.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    :param width: New width.
    :type width: :class:`int`
    :param height: New height.
    :type height: :class:`int`

    """
    driver = util.driver

    orig_size = driver.execute_script("""
    var height = wed_editor.$gui_root.height();
    var width = wed_editor.$gui_root.width();
    return {height: height, width: width};
    """)

    driver.set_window_size(width, height)

    def cond(*_):
        size = driver.execute_script("""
        var height = wed_editor.$gui_root.height();
        var width = wed_editor.$gui_root.width();
        return {height: height, width: width};
        """)
        return size != orig_size

    util.wait(cond)


def wait_for_editor(util, timeout=15):
    """
    Waits until the editor is initialized.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """
    driver = util.driver

    def cond(*_):
        return driver.execute_script(
            "return window.wed_editor && " +
            "wed_editor.getCondition('initialized');")

    with util.local_timeout(timeout):
        util.wait(cond)


def wait_for_first_validation_complete(util):
    """
    Waits until the editor is initialized.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """
    driver = util.driver

    def cond(*_):
        return driver.execute_script(
            "return window.wed_editor && " +
            "wed_editor.getCondition('first-validation-complete');")

    with util.local_timeout(15):
        util.wait(cond)


def wait_for_validation_complete(util):
    """
    Waits until the current validation is finished.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """
    driver = util.driver

    def cond(*_):
        return driver.execute_async_script("""
        var done = arguments[0];
        require(["wed/validator"], function (validator) {
            var state = window.wed_editor &&
                wed_editor.validator.getWorkingState().state;
            done(state === validator.VALID ||
                 state === validator.INVALID);
        });
        """)

    with util.local_timeout(5):
        util.wait(cond)


def wait_until_a_context_menu_is_not_visible(util):
    """
    Waits until a context menu is not visible.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """
    util.wait_until_not(EC.presence_of_element_located(
        (By.CLASS_NAME, "wed-context-menu")))


def wait_until_no_tooltip(util):
    """
    Waits until no tooltip is displayed.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """

    # The way we use tooltips, no tooltip displayed happens when there is
    # no tooltip as a child of body.
    util.wait_until_not(EC.presence_of_element_located(
        (By.CSS_SELECTOR, "body>.tooltip")))


def gui_root(util):
    """
    Gets the editor's GUI root.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    :returns: The root.
    :rtype: :class:`selenium.webdriver.remote.webelement.WebElement`
    """
    return util.driver.execute_script("return window.wed_editor.gui_root")


def get_label_visibility_level(util):
    """
    :returns: The visibility level.
    :rtype: :class:`int`
    """
    return util.driver.execute_script(
        "return window.wed_editor._current_label_level;")


def is_fatal_modal_present(util):
    """
    Tests whether the modal that is shown for fatal errors is present
    on the screen.

    :returns: Whether it is present or not.
    :rtype: :class:`bool`
    """
    return len(util.driver.find_elements_by_class_name("wed-fatal-modal")) > 0


def cut(util):
    """
    Initiates a cut operation.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """
    util.ctrl_equivalent_x("x")

    # It seems that Selenium does not support native events at all on OS X.
    if util.osx:
        util.driver.execute_script("""
        wed_editor.$gui_root.trigger("cut");
        """)


def paste(util):
    """
    Initiates a paste operation.

    :param util: The selenic util object.
    :type util: :class:`selenic.util.Util`
    """

    # It seems that Selenium does not support native events at all on OS X.
    if util.osx:
        raise Exception("""
        this cannot work on OS X. OS X does not support native events and a
        'paste' event cannot be simulated to the extent needed for the test
        suite.""")

    util.ctrl_equivalent_x("v")


def select_text_of_element_directly(util, selector):
    """
    This function is meant to be used to select text by direct
    manipulation of the DOM. This is meant for tests where we want to
    select text but we are not testing selection per se.

    .. warning:: This function will fail if an element has more than a
                 single text node.
    """
    driver = util.driver
    text = driver.execute_script("""
    var selector = arguments[0];
    var $el = jQuery(selector);
    var $text = $el.contents().filter(function () {
        return this.nodeType === Node.TEXT_NODE;
    });
    if ($text.length !== 1)
        throw new Error("the element must have exactly one text node");
    var caretManager = wed_editor.caretManager;
    var text = $text[0];
    caretManager.setRange(text, 0, text, text.length);
    return wed_editor.caretManager.range.toString();
    """, selector)

    return text


def select_contents_directly(util, selector):
    """
    This function is meant to be used to select text by direct
    manipulation of the DOM. This is meant for tests where we want to
    select text but we are not testing selection per se.

    :returns: The text of the selection. This is the text as
    understood by wed, so _phantom nodes are excluded.
    """
    text = util.driver.execute_script("""
    var $el = jQuery(arguments[0]);
    var el = $el[0];
    wed_editor.caretManager.setRange(el, 0, el, el.childNodes.length);
    var clone = el.cloneNode(true);
    var phantoms = clone.querySelectorAll("._phantom");
    for (var i = 0, phantom; (phantom = phantoms[i]) !== undefined; ++i)
        phantom.parentNode.removeChild(phantom);
    return clone.textContent;
    """, selector)

    return text


def select_directly(util, start_container, start_offset,
                    end_container, end_offset):
    """
    This function is meant to be used to select text by direct
    manipulation of the DOM. This is meant for tests where we want to
    select text but we are not testing selection per se.
    """
    text = util.driver.execute_script("""
    wed_editor.caretManager.setRange(arguments[0], arguments[1],
                                     arguments[2], arguments[3]);
    return range.toString();
    """, start_container, start_offset, end_container, end_offset)

    return text
