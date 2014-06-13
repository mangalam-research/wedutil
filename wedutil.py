"""
This module provides functions to check on the status of a wed
editor located at ``window.wed_editor``. Reading private variables
directly is fair game here.

"""

from distutils.version import StrictVersion

import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.common.by import By
import selenium

if StrictVersion(selenium.__version__) > StrictVersion("2.41.0"):
    raise Exception("check whether you still need the cut "
                    "rigmarole on OS X in this version of Selenium")


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
    var caret = wed_editor._raw_caret;
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


def caret_pos(driver):
    """
    Gets the ``x, y`` position of the caret relative to the
    screen.

    :param driver: The Selenium driver to operate on.
    :returns: The position.
    :rtype: ``{"left": x, "top": y}`` where ``x`` and ``y`` are
            the coordinates.
    """
    pos = driver.execute_script("""
    var pos = wed_editor._$fake_caret.offset();
    var $document = jQuery(document);
    pos.top -= $document.scrollTop();
    pos.left -= $document.scrollLeft();
    return pos;
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
    var pos = wed_editor._$fake_caret.offset();
    var $document = jQuery(document);
    pos.top -= $document.scrollTop();
    pos.left -= $document.scrollLeft();
    pos.top += wed_editor._$fake_caret.height() / 2;
    return pos;
    """)

    # ChromeDriver chokes on float values.
    pos["left"] = int(pos["left"])
    pos["top"] = int(pos["top"])
    return pos


def select_text(driver, start, end):
    """
    Sends commands to a Selenium driver to select text.

    :param driver: The Selenium driver to operate on.
    :param start: The start coordinates where to start the selection.
    :type start: ``{"left": x, "top": y}`` where ``x`` and ``y`` are
                 the coordinates.
    :param end: The end coordinates where to end the selection.
    :type end: ``{"left": x, "top": y}`` where ``x`` and ``y`` are
                 the coordinates.
    """

    #
    # This does not work...
    #
    # from selenium.webdriver.common.action_chains import ActionChains
    #
    # gui_root = driver.find_element_by_class_name("wed-document")
    #
    # ActionChains(driver)\
    #     .move_to_element_with_offset(gui_root, start["left"], start["top"])\
    #     .click_and_hold()\
    #     .move_to_element_with_offset(gui_root, end["left"], end["top"])\
    #     .release()\
    #     .perform()
    #
    # So...
    #

    # If this code fails, look at this issue:
    # http://code.google.com/p/selenium/issues/detail?id=6353
    driver.execute_async_script("""
    var $ = jQuery;
    var start = arguments[0];
    var end = arguments[1];
    var done = arguments[2];
    var $document = $(document);
    var scroll_top = $document.scrollTop();
    var scroll_left = $document.scrollLeft();
    var $gui_root = wed_editor.$gui_root;
    var event = new $.Event("mousedown");
    event.target = wed_editor.elementAtPointUnderLayers(start.left, start.top);
    event.clientX = start.left;
    event.clientY = start.top;
    event.pageX = start.left + scroll_left;
    event.pageY = start.top + scroll_top;
    event.which = 1;
    $gui_root.trigger(event);
    setTimeout(function () {
      var event = new $.Event("mousemove");
      event.target = wed_editor.elementAtPointUnderLayers(end.left, end.top);
      event.clientX = end.left;
      event.clientY = end.top;
      event.pageX = end.left + scroll_left;
      event.pageY = end.top + scroll_top;
      $gui_root.trigger(event);
      setTimeout(function () {
        var event = new $.Event("mouseup");
        // Recompute in the off-chance that something moved.
        event.target = wed_editor.elementAtPointUnderLayers(end.left, end.top);
        event.clientX = end.left;
        event.clientY = end.top;
        event.pageX = end.left + scroll_left;
        event.pageY = end.top + scroll_top;
        event.which = 1;
        $gui_root.trigger(event);
        var sel = window.getSelection();
        if (!sel.rangeCount || sel.getRangeAt(0).collapsed)
            throw new Error("no selection");
        done();
      }, 10);
    }, 10);
    """, start, end)


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


def wait_for_editor(util):
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

    with util.local_timeout(15):
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
