from __future__ import annotations

from typing import Any

"""Generated fallback stub for docassemble.base.functions."""

def alpha(num: Any, case: Any = ...) -> Any:
    """
    Return a letter label for a zero-based index (A, B, … Z, AA, AB, …).

    Args:
        num (int): The zero-based index.
        case (str, optional): ``'upper'`` for uppercase (default) or
            ``'lower'`` for lowercase.

    Returns:
        str: The alphabetical label (e.g. ``alpha(0)`` returns ``'A'``,
            ``alpha(25)`` returns ``'Z'``, ``alpha(26)`` returns ``'AA'``).
    """
    ...

def roman(num: Any, case: Any = ...) -> Any:
    """
    Return a Roman numeral for a zero-based index.

    Args:
        num (int): The zero-based index (0–3998).
        case (str, optional): ``'upper'`` for uppercase (default) or
            ``'lower'`` for lowercase.

    Returns:
        str: The Roman numeral for ``num + 1`` (e.g. ``roman(0)`` returns
            ``'I'``, ``roman(65)`` returns ``'LXVI'``).

    Raises:
        ValueError: If ``num + 1`` is not between 1 and 3999.
        TypeError: If ``num`` is not an integer.
    """
    ...

def item_label(num: Any, level: Any = ..., punctuation: Any = ...) -> Any:
    """
    Return a formatted list item label for a given zero-based index and outline level.

    Args:
        num (int): The zero-based index of the item.
        level (int, optional): The outline level (0–6).  Level 0 uses
            Roman numerals, 1 uses uppercase letters, 2 and 4 use Arabic
            numerals, 3 and 5 use lowercase letters, 6 uses lowercase Roman
            numerals. Defaults to ``0``.
        punctuation (bool, optional): If ``True``, appends the appropriate
            punctuation mark. Defaults to ``True``.

    Returns:
        str: The formatted label (e.g. ``'I.'``, ``'A.'``, ``'1.'``,
            ``'a)'``, ``'(1)'``, ``'(a)'``, ``'i)'``).
    """
    ...

ordinal: Any

ordinal_number: Any

comma_list: Any

def word(the_word: Any, **kwargs: Any) -> Any:
    """
    Return the word translated into the current language.

    If no translation is found for the current language, the input is
    returned unchanged.  Used throughout docassemble to support
    multilingual interviews.

    Args:
        the_word (str): The word or phrase to translate.
        **kwargs: Optional keyword arguments.  Pass ``language`` to
            look up a translation for a specific language, or
            ``capitalize=True`` to capitalize the result.

    Returns:
        str: The translated (or original) word.
    """
    ...

def get_language() -> Any:
    """
    Return the current language code.

    Returns:
        str: The current language code (e.g., ``'en'``, ``'es'``).
    """
    ...

def set_language(lang: Any, dialect: Any = ..., voice: Any = ...) -> Any:
    """
    Set the language used for linguistic functions and the web application.

    Does not change the Python locale; call ``update_locale()`` for that.
    Should be called in an ``initial`` code block so it takes effect on every
    page load.

    Args:
        lang (str): A lowercase ISO-639-1 or ISO-639-3 language code
            (e.g., ``'en'``, ``'es'``, ``'fr'``).
        dialect (str, optional): A dialect code for the text-to-speech engine.
            Defaults to None.
        voice (str, optional): A voice name for the text-to-speech engine.
            Defaults to None.
    """
    ...

def get_dialect() -> Any:
    """
    Return the current dialect.

    Returns:
        str: The dialect code set by the ``dialect`` keyword argument to
            :func:`set_language`, or ``None`` if no dialect has been set.
    """
    ...

def set_country(country: Any) -> Any:
    """
    Set the current country used for phone number formatting and other locale features.

    Args:
        country (str): A two-letter uppercase ISO 3166-1 alpha-2 country code
            (e.g., ``'US'``, ``'GB'``, ``'DE'``).
    """
    ...

def get_country() -> Any:
    """
    Return the current country code.

    Returns:
        str: A two-letter uppercase ISO 3166-1 alpha-2 country code
            (e.g., ``'US'``). Defaults to ``'US'`` unless configured otherwise.
    """
    ...

def get_locale(*pargs: Any) -> Any:
    """
    Return the current locale setting or a specific locale convention.

    With no arguments, returns the locale string previously set with
    :func:`set_locale`.  With one argument, returns the value of the named
    locale convention (e.g. ``'currency_symbol'``), taking into account any
    overrides set with :func:`set_locale`.

    Args:
        *pargs: An optional locale convention name (e.g.
            ``'currency_symbol'``).

    Returns:
        str or None: The locale string when called with no arguments, or the
            value of the requested locale convention (``None`` if not found).
    """
    ...

def set_locale(*pargs: Any, **kwargs: Any) -> Any:
    """
    Set the current locale string and/or locale convention overrides.

    Calling ``set_locale('FR.utf8')`` stores the locale string so that
    :func:`get_locale` returns it.  The actual Python locale does not change
    until :func:`update_locale` is called.  Keyword arguments such as
    ``currency_symbol`` override individual locale conventions used by
    functions like :func:`currency` and :func:`currency_symbol`.

    Args:
        *pargs: An optional locale string (e.g. ``'FR.utf8'``).
        **kwargs: Locale convention overrides (e.g. ``currency_symbol='€'``).
    """
    ...

comma_and_list: Any

def need(*pargs: Any) -> Any:
    """
    Ensure that the given variables are defined, asking questions if necessary.

    Evaluating each argument causes docassemble to seek its definition
    through the normal interview logic.  The function always returns
    ``True``.  Using ``need()`` is purely for readability; writing
    ``need(x, y)`` is equivalent to writing ``x; y`` in a code block.

    Args:
        *pargs: Variables whose definitions should be ensured.

    Returns:
        bool: Always ``True``.
    """
    ...

nice_number: Any

quantity_noun: Any

currency_symbol: Any

verb_past: Any

verb_present: Any

noun_plural: Any

noun_singular: Any

indefinite_article: Any

capitalize: Any

def space_to_underscore(a: Any) -> Any:
    """
    Convert spaces to underscores and sanitize the input for use as a filename.

    Replaces spaces with underscores and removes characters that are not safe
    for filenames using Werkzeug's ``secure_filename``.

    Args:
        a: The value to convert (coerced to a string).

    Returns:
        str: A filename-safe string with spaces replaced by underscores.
    """
    ...

def force_ask(*pargs: Any, **kwargs: Any) -> Any:
    """
    Force docassemble to ask one or more questions, even if the variables are already defined.

    Triggers the actions mechanism so that the interview shows a question
    corresponding to each specified variable name, regardless of whether the
    variable is already defined.  Code after ``force_ask()`` is never reached.
    Variable names must be passed as strings.

    Args:
        *pargs: Variable name strings (or action dictionaries) identifying
            the questions to ask.
        **kwargs: Optional keyword arguments including ``forget_prior``
            (bool, default ``False``) to clear pending actions before
            adding new ones, and ``evaluate`` (bool, default ``False``) to
            resolve alias variable names to their intrinsic names.
    """
    ...

period_list: Any

name_suffix: Any

currency: Any

def static_image(filereference: Any, width: Any = ...) -> Any:
    """
    Return the markup string to embed a static image.

    Produces a ``[FILE ...]`` markup tag that docassemble renders as an
    image.  Useful when the image path is assembled programmatically
    rather than written literally in a template.

    Args:
        filereference (str): A package-qualified file reference such as
            ``'docassemble.demo:crawling.png'``, or just ``'crawling.png'``
            for a file in the current package.
        width (str, optional): The display width, e.g. ``'2in'`` or
            ``'50%'``. Defaults to ``None`` (no explicit width).

    Returns:
        str: A ``[FILE ...]`` markup string, or an error string if the
            reference is invalid.
    """
    ...

title_case: Any

def url_of(file_reference: Any, **kwargs: Any) -> Any:
    """
    Return a URL to a file within a docassemble package or to a page in the application.

    The ``file_reference`` can be a filename like ``'brochure.pdf'`` (relative
    to the current package's ``static`` folder), a package-qualified reference
    like ``'docassemble.mypackage:data/static/file.pdf'``, a ``DAFile`` object,
    or one of several special strings (``'login'``, ``'register'``, ``'root'``,
    ``'interview'``, ``'temp_url'``, ``'login_url'``, etc.). Keyword arguments
    are passed as URL parameters.

    Args:
        file_reference: A filename, package-qualified reference, DAFile object,
            or special string identifying the target.
        **kwargs: Additional URL parameters or control arguments like
            ``_external=True`` for a full URL or ``_attachment=True`` to
            trigger a download.

    Returns:
        str: A URL string.
    """
    ...

def process_action() -> Any:
    """
    Process any pending interview action.

    Checks whether an action has been requested (e.g., via a URL created by
    :func:`url_action`) and, if so, handles it by calling :func:`force_ask`
    on the indicated variable.  If no action is pending, returns without
    doing anything.  This function is normally called automatically by
    docassemble before evaluating ``initial`` and ``mandatory`` blocks, but
    you can call it explicitly to control when actions are processed.
    """
    ...

def url_action(action: Any, **kwargs: Any) -> Any:
    """
    Return a URL that triggers an action in the current interview.

    When visited, the URL causes :func:`process_action` to run the specified
    action.  The action can run a code block labeled with ``event``, ask a
    question, or define a variable.

    Args:
        action (str): The name of the action (variable or event) to trigger.
        **kwargs: Arguments to pass to the action.  The special keyword
            argument ``_forget_prior`` (bool), if ``True``, discards any
            currently pending actions before running this one.

    Returns:
        str: A URL string that triggers the action when visited.
    """
    ...

def get_info(att: Any) -> Any:
    """
    Return the value of a global variable previously set with ``set_info()``.

    Args:
        att (str): The name of the attribute to retrieve.

    Returns:
        The value that was set for the attribute, or None if it was never set.
    """
    ...

def set_info(**kwargs: Any) -> Any:
    """
    Store global variables for later retrieval with ``get_info()``.

    Typically called in an ``initial`` code block so the values are refreshed
    on every page load. Common usage includes setting ``user`` and ``role``.

    Args:
        **kwargs: Keyword arguments whose names become attribute names and
            whose values are stored for later retrieval.
    """
    ...

def get_config(key: Any, none_value: Any = ...) -> Any:
    """
    Return a value from the docassemble configuration file.

    Args:
        key (str): The configuration directive to look up.
        none_value (optional): The value to return if the key is not found in
            the configuration. Defaults to None.

    Returns:
        The configuration value associated with the key, or ``none_value``
            if the key is not present.
    """
    ...

def prevent_going_back() -> Any:
    """
    Disable the back button so the user cannot revisit previous questions.

    Once called, the user will not be able to go back and change any answers
    entered before this point in the interview.
    """
    ...

def qr_code(string: Any, width: Any = ..., alt_text: Any = ...) -> Any:
    """
    Return the markup string to embed a QR code image for the given string.

    Produces a ``[QR ...]`` markup tag that docassemble renders as a QR
    code image.  Useful when the string to encode is assembled
    programmatically rather than written literally in a template.

    Args:
        string (str): The text or URL to encode in the QR code.
        width (str, optional): The display width, e.g. ``'2in'``. Defaults
            to ``None`` (no explicit width).
        alt_text (str, optional): The alt text for the image. Defaults to
            ``None``.

    Returns:
        str: A ``[QR ...]`` markup string.
    """
    ...

def action_menu_item(label: Any, action: Any, **kwargs: Any) -> Any:
    """
    Return a menu item dictionary that triggers an action when clicked.

    Constructs a dictionary with a ``label`` and a ``url`` (created via
    :func:`url_action`) for use in the ``menu_items`` special variable.

    Args:
        label (str): The text displayed in the menu.
        action (str): The action name to trigger when the item is clicked.
        **kwargs: Arguments passed on to the action via :func:`url_action`.
            The special argument ``_screen_size`` (``'small'`` or
            ``'large'``) restricts the item to the given screen size.

    Returns:
        dict: A dictionary with keys ``label`` and ``url``, and optionally
            ``screen_size``.
    """
    ...

def from_b64_json(string: Any) -> Any:
    """
    Decode a base-64 string and parse it as JSON, returning the resulting object.

    This is an advanced function used to integrate external systems with
    docassemble by decoding data that was encoded with base-64 JSON encoding.

    Args:
        string (str): A base-64-encoded JSON string, or ``None``.

    Returns:
        The Python object represented by the decoded JSON, or ``None`` if
            ``string`` is ``None``.
    """
    ...

def defined(var: str, prior: Any = ...) -> bool:
    """
    Return ``True`` if the named interview variable is already defined.

    Checks whether the variable is defined without triggering docassemble's
    question-asking process.  The variable name must be passed as a string.

    Args:
        var (str): The name of the variable to check.
        prior (bool, optional): If ``True``, on screens loaded after the
            user pressed the Back button, also check the previous set of
            interview answers. Defaults to ``False``.

    Returns:
        bool: ``True`` if the variable is defined, ``False`` otherwise.
    """
    ...

def value(var: str, prior: Any = ...) -> Any:
    """
    Return the value of an interview variable specified by name.

    Equivalent to evaluating the variable directly, but uses a string for
    the variable name.  If the variable is not yet defined, docassemble will
    ask questions to define it.

    Args:
        var (str): The name of the variable whose value to return.
        prior (bool, optional): If ``True``, on screens loaded after the
            user pressed the Back button, look in the previous set of
            interview answers. Defaults to ``False``.

    Returns:
        The value of the specified variable.
    """
    ...

def message(*pargs: Any, **kwargs: Any) -> Any:
    """
    Stop the interview and present a message screen to the user.

    Raises a ``QuestionError`` so that docassemble immediately shows a screen
    with the given title and optional subquestion text.  Code after
    ``message()`` is never executed.

    Args:
        *pargs: Positional arguments passed to the underlying
            ``QuestionError``.  The first argument is the title
            (``question``) and the optional second argument is the body
            (``subquestion``).
        **kwargs: Keyword arguments such as ``question``, ``subquestion``,
            ``show_restart``, ``show_exit``, ``show_leave``, ``url``, and
            ``buttons``.
    """
    ...

def response(*pargs: Any, **kwargs: Any) -> Any:
    """
    Send a custom HTTP response instead of the normal interview screen.

    Raises a ``ResponseError`` so that docassemble immediately returns the
    specified content to the client.  Code after ``response()`` is never
    executed.

    Args:
        *pargs: Positional arguments passed to the underlying
            ``ResponseError``.
        **kwargs: Keyword arguments specifying the response type and
            content.  Use one of: ``response`` (text), ``binaryresponse``
            (bytes), ``file`` (``DAFile`` or package reference), or ``url``
            (redirect target).  Optional: ``content_type`` and
            ``response_code`` (default ``200``).
    """
    ...

def json_response(data: Any, response_code: Any = ...) -> Any:
    """
    Send the given data as a JSON HTTP response.

    A shorthand for calling :func:`response` with a JSON-encoded binary
    body and ``content_type='application/json'``.  Code after
    ``json_response()`` is never executed.

    Args:
        data: The data to serialize and return as JSON.
        response_code (int, optional): The HTTP response code. Defaults to
            ``200``.
    """
    ...

def command(*pargs: Any, **kwargs: Any) -> Any:
    """
    Trigger an interview exit command such as exit, logout, or restart.

    Raises a ``CommandError`` so that docassemble immediately processes the
    specified command.  Code after ``command()`` is never executed.

    Args:
        *pargs: The command string as the first positional argument.  Valid
            values are ``'restart'``, ``'new_session'``, ``'exit'``,
            ``'logout'``, ``'exit_logout'``, ``'leave'``, and
            ``'signin'``.
        **kwargs: Optional keyword arguments such as ``url`` (the redirect
            target) and ``sleep`` (seconds to pause in scheduled tasks).
    """
    ...

def background_response(*pargs: Any, **kwargs: Any) -> Any:
    """
    Finish a background task and optionally return a result.

    Must be called at the end of every background action code block.
    When called with a value, that value is retrievable via ``.get()``
    on the task object.  Can also be called with keyword arguments to
    populate target areas on the screen, set field values, run
    JavaScript, or trigger a screen refresh.

    Args:
        *pargs: An optional return value, or special control strings
            such as ``'refresh'``, ``'javascript'``, ``'flash'``, or
            ``'fields'``.
        **kwargs: Optional keyword arguments such as ``target`` and
            ``content`` for populating ``[TARGET ...]`` areas.
    """
    ...

def background_response_action(*pargs: Any, **kwargs: Any) -> Any:
    """
    Finish a background task by triggering an action to save values to the interview dictionary.

    Use this instead of :func:`background_response` when the background task
    needs to persist changes to interview variables.  The first argument is
    the name of the action to run; keyword arguments are passed to that action.

    Args:
        *pargs: The action name as the first positional argument.
        **kwargs: Arguments to pass to the specified action.
    """
    ...

def single_paragraph(text: Any) -> Any:
    """
    Replace all line breaks in the text with spaces, collapsing it to a single paragraph.

    Useful when embedding user-supplied text in a Markdown block-quote or
    similar context where internal line breaks would break the formatting.

    Args:
        text (str): The text to process.

    Returns:
        str: The text with all newline characters replaced by spaces.
    """
    ...

def quote_paragraphs(text: Any) -> Any:
    """
    Wrap each paragraph in the text with Markdown block-quote formatting.

    Adds ``> `` before each paragraph so that the text is displayed as a
    Markdown block-quote.

    Args:
        text (str): The text to quote.

    Returns:
        str: The text with each paragraph prefixed by ``'> '``.
    """
    ...

def location_returned() -> Any:
    """
    Return True if an attempt has been made to transmit the user's GPS location.

    Returns True even if the attempt was unsuccessful or the user refused to
    consent to the transfer. Use ``location_known()`` to test whether the
    location was successfully obtained.

    Returns:
        bool: True if a location transmission has been attempted, False otherwise.
    """
    ...

def location_known() -> Any:
    """
    Return True if docassemble successfully obtained the user's GPS location.

    Returns:
        bool: True if the user's latitude and longitude are known, False otherwise.
    """
    ...

def user_lat_lon() -> Any:
    """
    Return the user's latitude and longitude as a tuple.

    Returns:
        tuple: A ``(latitude, longitude)`` tuple of floats if the location is
            known, or ``(None, None)`` if the location is not available. If
            there was a location error, returns ``(error_message, error_message)``.
    """
    ...

def interview_url(**kwargs: Any) -> Any:
    """
    Return a URL that links directly to the current interview session.

    Used in multi-user interviews to invite additional users to participate.
    Keyword arguments are included as URL parameters. Special keyword arguments
    include ``i`` (interview filename), ``session`` (session ID), ``local``
    (return a relative URL), ``new_session``, ``reset``, ``style``,
    ``temporary`` (expire in N hours), and ``once_temporary``.

    Returns:
        str: A URL string pointing to the interview session.
    """
    ...

def interview_url_action(action: Any, **kwargs: Any) -> Any:
    """
    Return a URL that links to the interview and triggers a specified action.

    Like ``interview_url()``, but additionally encodes an action to run when
    the URL is visited. Keyword arguments are passed as action arguments, except
    for ``i``, ``session``, ``local``, ``new_session``, ``reset``,
    ``_forget_prior``, ``style``, ``temporary``, and ``once_temporary``, which
    control the URL behavior.

    Args:
        action (str): The name of the action to trigger.
        **kwargs: Arguments to the action and URL modifiers.

    Returns:
        str: A URL string that will trigger the specified action when visited.
    """
    ...

def interview_url_as_qr(**kwargs: Any) -> Any:
    """
    Return markup for a QR code linking to the current interview session.

    Can be used to pass control from a web browser or a paper handout to a
    mobile device. Accepts the same keyword arguments as ``interview_url()``,
    plus ``alt_text`` and ``width`` for the QR code image.

    Returns:
        str: Markup string containing a QR code image linking to the interview.
    """
    ...

def interview_url_action_as_qr(action: Any, **kwargs: Any) -> Any:
    """
    Return markup for a QR code linking to the interview with a specified action.

    Like ``interview_url_as_qr()``, but the URL encodes an action to run when
    visited. Accepts the same keyword arguments as ``interview_url_action()``,
    plus ``alt_text`` and ``width`` for the QR code image.

    Args:
        action (str): The name of the action to trigger when the QR code is scanned.
        **kwargs: Arguments to the action and URL/image modifiers.

    Returns:
        str: Markup string containing a QR code image linking to the action URL.
    """
    ...

def interview_email(key: Any = ..., index: Any = ...) -> Any:
    """
    Return an e-mail address that routes incoming messages to this interview session.

    The address is a unique random identifier at the configured incoming mail
    domain. Every call with the same ``key`` and ``index`` returns the same address.

    Args:
        key (str, optional): A label to distinguish different e-mail addresses
            for the same session (e.g., ``'evidence'``, ``'opposing counsel'``).
            Defaults to None.
        index (int, optional): An integer to further distinguish addresses under
            the same ``key``. Requires ``key`` to be set. Defaults to None.

    Returns:
        str: An e-mail address string (e.g., ``'kgjeir@help.example.com'``).
    """
    ...

def get_emails(key: Any = ..., index: Any = ...) -> Any:
    """
    Return information about e-mail addresses and messages for this interview session.

    Returns a list of objects, each with attributes ``address``, ``emails``,
    ``key``, and ``index``.

    Args:
        key (str, optional): Filter results to addresses created with this key.
            Defaults to None (returns all addresses).
        index (int, optional): Further filter to the address with this index
            under the given ``key``. Defaults to None.

    Returns:
        list: A list of objects representing e-mail addresses and their received
            messages.
    """
    ...

def action_arguments() -> Any:
    """
    Return a dictionary of arguments passed to the current action.

    Used when processing an action triggered by ``url_action()`` or
    ``interview_url_action()``. The special keys ``_initial`` and ``_changed``
    are excluded from the result.

    Returns:
        dict: A dictionary of keyword arguments passed to the action, or an
            empty dictionary if no arguments were provided.
    """
    ...

def action_argument(item: Any = ...) -> Any:
    """
    Return the value of a named argument for the current action.

    Used when processing an action triggered by ``url_action()`` or
    ``interview_url_action()``. If called without an argument, returns the
    name of the action itself (useful in ``initial`` blocks before calling
    ``process_action()``). Returns None if no action is active.

    Args:
        item (str, optional): The name of the argument to retrieve. If omitted,
            the name of the action itself is returned. Defaults to None.

    Returns:
        The value of the specified argument, the action name (if ``item`` is
            None), or None if the action or argument is not found.
    """
    ...

def get_default_timezone() -> Any:
    """
    Return the default timezone string for the server.

    Returns the server's local timezone unless a default timezone is configured
    in the docassemble configuration.

    Returns:
        str: A timezone string such as ``'America/New_York'``.
    """
    ...

def user_logged_in() -> Any:
    """
    Return True if the user is logged in, False otherwise.

    Returns:
        bool: True if the current user is authenticated, False otherwise.
    """
    ...

def user_privileges() -> Any:
    """
    Return a list of the current user's privileges.

    For users who are not logged in, this is always ``['user']``. For
    scheduled tasks, this is ``['cron']``.

    Returns:
        list: A list of privilege strings (e.g., ``['user', 'admin']``).
    """
    ...

def user_has_privilege(*pargs: Any) -> Any:
    """
    Return True if the current user has any of the given privileges.

    Args:
        *pargs: One or more privilege names (strings) or lists of privilege
            names. Returns True if the user holds any of the named privileges.

    Returns:
        bool: True if the user has at least one of the specified privileges,
            False otherwise.
    """
    ...

def user_info() -> Any:
    """
    Return an object with information about the current user's profile.

    The returned object has attributes including ``id``, ``first_name``,
    ``last_name``, ``email``, ``login_method``, ``phone_number``, ``country``,
    ``subdivision_first``, ``subdivision_second``, ``subdivision_third``,
    ``organization``, ``language``, ``timezone``, and ``privileges``.

    Returns:
        TheUser: An object with attributes describing the current user.
    """
    ...

def current_context() -> Any:
    """
    Return an object describing the context in which Python code is executing.

    The returned object has attributes including ``session``, ``filename``,
    ``package``, ``question_id``, ``current_filename``, ``current_package``,
    ``variable``, ``current_section``, ``inside_of``, ``attachment``, and
    ``request_url``.

    Returns:
        TheContext: An object with context attributes for the current execution.
    """
    ...

def background_action(*pargs: Any, **kwargs: Any) -> Any:
    """
    Start an interview action as a background (Celery) task and return immediately.

    The specified action runs asynchronously in a Celery worker.  Returns a
    task object whose ``.ready()``, ``.failed()``, ``.wait()``, ``.get()``,
    and ``.result()`` methods can be used to monitor and retrieve the result.

    Args:
        *pargs: The action name as the first positional argument, and an
            optional second argument for the UI notification mode.
        **kwargs: Arguments to pass to the action, accessible inside the
            action via :func:`action_argument`.

    Returns:
        A task object representing the background task.
    """
    ...

us: Any

def set_live_help_status(availability: Any = ..., mode: Any = ..., partner_roles: Any = ...) -> Any:
    """
    Configure the live help (chat) feature for the current interview session.

    Args:
        availability (str or bool, optional): Set to ``'available'`` or
            ``True`` to enable live help, ``'unavailable'`` or ``False``
            to disable it, or ``'observeonly'`` to allow the monitor to
            observe but not chat.
        mode (str, optional): Chat mode; one of ``'help'``, ``'peer'``,
            or ``'peerhelp'``.
        partner_roles (str or list, optional): The roles of monitors with
            whom the user may chat.
    """
    ...

def chat_partners_available(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return the number of chat partners available to the user.

    Args:
        *pargs: One or more partner role names (strings or lists of strings)
            to include as valid chat partners.
        partner_roles (list, optional): Additional partner roles. Defaults to [].
        mode (str, optional): The chat mode, e.g., ``'peerhelp'``. Defaults to
            ``'peerhelp'``.

    Returns:
        dict: A dictionary with keys ``'peer'`` and ``'help'``, each mapping to
            an integer count of available partners.
    """
    ...

def phone_number_in_e164(number: Any, country: Any = ...) -> Any:
    """
    Return a phone number formatted in E.164 international format.

    Args:
        number (str): The phone number to format.
        country (str, optional): An ISO 3166-1 alpha-2 country code (e.g.
            ``'US'``, ``'SE'``) used to interpret the number. Defaults to
            the result of :func:`get_country`.

    Returns:
        str or None: The number in E.164 format (e.g. ``'+12025551234'``),
            or ``None`` if the number could not be formatted.
    """
    ...

def phone_number_formatted(number: Any, country: Any = ...) -> Any:
    """
    Return a phone number in the national format for the specified country.

    Args:
        number (str): The phone number to format.
        country (str, optional): An ISO 3166-1 alpha-2 country code used
            to determine national formatting conventions. Defaults to the
            result of :func:`get_country`.

    Returns:
        str or None: The number in national format, or ``None`` if the
            number could not be formatted.
    """
    ...

def phone_number_is_valid(number: Any, country: Any = ...) -> Any:
    """
    Return ``True`` if the phone number is valid for the specified country.

    Args:
        number (str): The phone number to validate.
        country (str, optional): An ISO 3166-1 alpha-2 country code used
            to determine applicable standards. Defaults to the result of
            :func:`get_country`.

    Returns:
        bool: ``True`` if the number is valid, ``False`` otherwise.
    """
    ...

def countries_list() -> Any:
    """
    Return a list of countries sorted by name, suitable for use in a multiple-choice field.

    Each element in the list is a single-key dictionary mapping the two-letter
    ISO 3166-1 alpha-2 country code to the country name.

    Returns:
        list: A list of dicts, each mapping a country code (str) to a country name (str).
    """
    ...

def country_name(country_code: Any) -> Any:
    """
    Return the full name of a country given its two-letter ISO 3166-1 alpha-2 code.

    The name is passed through the ``word()`` function for translation.

    Args:
        country_code (str): A two-letter, capitalized country code (e.g., ``'US'``, ``'DE'``).

    Returns:
        str: The full name of the country in the current language.
    """
    ...

def write_record(key: Any, data: Any) -> Any:
    """
    Store data in the SQL database under the given key.

    Args:
        key (str): A string key to associate with the record.
        data: The data to store. Must be pickleable.

    Returns:
        int: The unique integer ID of the saved record.
    """
    ...

def read_records(key: Any) -> Any:
    """
    Return all records stored under the given key.

    Args:
        key (str): The string key used when calling ``write_record()``.

    Returns:
        dict: A dictionary mapping unique integer record IDs to the stored data.
    """
    ...

def delete_record(key: Any, the_id: Any) -> Any:
    """
    Delete a record from the SQL database by key and ID.

    Args:
        key (str): The string key associated with the record.
        the_id (int): The unique integer ID of the record to delete.
    """
    ...

def variables_as_json(include_internal: Any = ...) -> Any:
    """
    Send all interview session variables as a JSON HTTP response.

    Like :func:`all_variables` combined with :func:`json_response`: returns
    all interview variables in simplified, JSON-serializable form.  Code
    after ``variables_as_json()`` is never executed.

    Args:
        include_internal (bool, optional): If ``True``, includes the
            ``_internal`` and ``nav`` variables in the output. Defaults to
            ``False``.
    """
    ...

def all_variables(simplify: Any = ..., include_internal: Any = ..., special: Any = ..., make_copy: Any = ...) -> Any:
    """
    Return the interview session variables as a dictionary.

    By default, returns a simplified dictionary suitable for JSON
    serialization (objects converted to dicts, dates to ISO strings).
    Use ``simplify=False`` for the raw Python dictionary.

    Args:
        simplify (bool, optional): If ``True`` (default), converts objects
            to JSON-friendly representations. If ``False``, returns the raw
            Python dictionary.
        include_internal (bool, optional): If ``True``, includes the
            ``_internal`` and ``nav`` variables. Defaults to ``False``.
        special (str or bool, optional): Pass ``'titles'`` to return
            interview title metadata, ``'metadata'`` to return consolidated
            metadata, or ``'tags'`` to return the current session tags.
            Defaults to ``False``.
        make_copy (bool, optional): When ``simplify=False``, if ``True``
            returns a deep copy of the dictionary. Defaults to ``False``.

    Returns:
        dict or set: The interview variables dictionary, or a set of tags
            when ``special='tags'``.
    """
    ...

def language_from_browser(*pargs: Any) -> Any:
    """
    Return the user's preferred language based on the browser's Accept-Language header.

    Reads the Accept-Language HTTP header and returns the first recognized
    ISO-639-1, ISO-639-2, or ISO-639-3 language code. If called with arguments,
    only languages in the argument list are considered valid.

    Args:
        *pargs: Optional list of valid language codes. If provided, only these
            codes are considered, and None is returned if the browser's preferred
            language is not in the list.

    Returns:
        str: A language code (e.g., ``'en'``, ``'es'``) or None if the language
            cannot be determined.
    """
    ...

def device(ip: Any = ...) -> Any:
    """
    Return information about the user's device or IP address.

    Args:
        ip (bool, optional): If True, return the user's IP address as a string
            instead of device information. Defaults to False.

    Returns:
        object: A user-agent object with browser and device information, or
            a string IP address when ``ip=True``. Returns None if device
            information cannot be determined.
    """
    ...

def plain(text: Any, default: Any = ...) -> Any:
    """
    Return the text as-is, or an empty string (or default) if the text is blank.

    Useful in templates when you want blank values to produce no output
    instead of an empty string.

    Args:
        text: The value to return.
        default (optional): Value to return if ``text`` is blank or
            ``None``. Defaults to ``None`` (returns ``''``).

    Returns:
        str: The text, or the default value if the text is empty.
    """
    ...

def bold(text: Any, default: Any = ...) -> Any:
    """
    Return the text wrapped in Markdown bold formatting, or an empty string if blank.

    If ``text`` is empty and ``default`` is provided, wraps ``default`` in
    bold formatting instead.

    Args:
        text: The value to make bold.
        default (optional): Fallback value (also bolded) if ``text`` is
            blank. Defaults to ``None`` (returns ``''``).

    Returns:
        str: The text wrapped in ``**...**`` Markdown, or ``''`` if blank
            and no default is given.
    """
    ...

def italic(text: Any, default: Any = ...) -> Any:
    """
    Return the text wrapped in Markdown italic formatting, or an empty string if blank.

    If ``text`` is empty and ``default`` is provided, wraps ``default`` in
    italic formatting instead.

    Args:
        text: The value to make italic.
        default (optional): Fallback value (also italicized) if ``text``
            is blank. Defaults to ``None`` (returns ``''``).

    Returns:
        str: The text wrapped in ``_..._`` Markdown, or ``''`` if blank
            and no default is given.
    """
    ...

def subdivision_type(country_code: Any) -> Any:
    """
    Return the name of the primary subdivision type for the given country.

    For example, returns ``'State'`` for ``'US'``, ``'Province'`` for ``'CA'``.
    Returns None if the country has no subdivisions.

    Args:
        country_code (str): A two-letter ISO 3166-1 alpha-2 country code.

    Returns:
        str: The name of the most common first-level subdivision type, or None
            if the country has no subdivisions.
    """
    ...

def indent(text: Any, by: Any = ...) -> Any:
    """
    Indent each line of the text by a number of spaces.

    Useful when embedding a paragraph or table inside a Markdown bulleted
    list to keep the content associated with the list item.

    Args:
        text (str): The text to indent.
        by (int, optional): Number of spaces to add at the start of each
            line. Defaults to ``4``.

    Returns:
        str: The text with each line prefixed by the specified number of
            spaces.
    """
    ...

def raw(val: Any) -> Any:
    """
    Pass a value as-is to a DOCX template without converting it to text.

    Wraps the value so that Jinja2 template code can use it directly,
    for example as a list or other Python object rather than a string.

    Args:
        val: The value to pass through without text conversion.

    Returns:
        RawValue: A wrapper object containing the original value.
    """
    ...

def fix_punctuation(text: Any, mark: Any = ..., other_marks: Any = ...) -> Any:
    """
    Ensure the text ends with a punctuation mark, adding one if necessary.

    Args:
        text (str): The text to check.
        mark (str, optional): The punctuation mark to append if none is
            present. Defaults to ``'.'``.
        other_marks (list, optional): A list of punctuation marks that are
            considered acceptable endings. Defaults to ``['.', '?', '!']``.

    Returns:
        str: The text, possibly with a punctuation mark appended.
    """
    ...

def set_progress(number: Any) -> Any:
    """
    Set the position of the interview progress meter.

    Args:
        number (int or float): The progress value to display. Pass None to
            hide the progress meter.
    """
    ...

def get_progress() -> Any:
    """
    Return the current value of the interview progress meter.

    Returns:
        int or float: The current progress value.
    """
    ...

def referring_url(default: Any = ..., current: Any = ...) -> Any:
    """
    Return the URL that the user was visiting when the interview session was created.

    Retrieves the HTTP Referer URL recorded when the session started.  If
    the URL is unavailable (e.g., the user typed the URL directly), returns
    the ``default`` value or the ``exitpage`` configuration setting.

    Args:
        default (optional): Value to return if the referring URL is not
            available. If ``None``, falls back to the ``exitpage``
            configuration setting. Defaults to ``None``.
        current (bool, optional): If ``True``, returns the Referer of the
            current request instead of the session-start Referer. Defaults
            to ``False``.

    Returns:
        str: The referring URL, the ``default`` value, or the ``exitpage``
            URL.
    """
    ...

def undefine(*pargs: Any, invalidate: Any = ...) -> Any:
    """
    Delete one or more interview variables, making them undefined.

    If a variable is not defined, this function does nothing (no error is
    raised).  Multiple variable names can be passed at once.

    Args:
        *pargs: Variable name strings to undefine.
        invalidate (bool, optional): Internal flag; when ``True``, also
            saves the current value for use as a default. Use
            :func:`invalidate` instead of setting this directly. Defaults
            to ``False``.
    """
    ...

def invalidate(*pargs: Any) -> Any:
    """
    Make one or more variables undefined while remembering their prior values as defaults.

    Like :func:`undefine`, but also stores the current value so that it is
    offered as a default when the question is re-asked.

    Args:
        *pargs: Variable name strings to invalidate.
    """
    ...

def dispatch(var: Any) -> Any:
    """
    Present a nested menu driven by the value of a variable.

    Repeatedly evaluates the variable named by ``var``.  When the variable
    is set to the name of another variable, that variable is evaluated and
    then undefined, allowing the user to visit sub-menus or pages.  The
    loop ends when the variable is set to ``None``.

    Args:
        var (str): The name of the variable that controls the menu
            selection.

    Returns:
        bool: Always ``True``.
    """
    ...

def yesno(the_value: Any, invert: Any = ...) -> Any:
    """
    Return ``'Yes'`` or ``'No'`` based on the truth value of the argument.

    Useful for populating PDF checkbox fields that expect ``'Yes'`` or
    ``'No'`` strings.

    Args:
        the_value: The value to evaluate.
        invert (bool, optional): If ``True``, returns ``'No'`` for truthy
            values and ``'Yes'`` for falsy values. Defaults to ``False``.

    Returns:
        str: ``'Yes'`` or ``'No'``, or ``''`` if the value is empty.
    """
    ...

def noyes(the_value: Any, invert: Any = ...) -> Any:
    """
    Return ``'No'`` or ``'Yes'`` based on the truth value of the argument.

    The inverse of :func:`yesno`: returns ``'No'`` for truthy values and
    ``'Yes'`` for falsy values.  Useful for populating PDF checkbox fields.

    Args:
        the_value: The value to evaluate.
        invert (bool, optional): If ``True``, reverses the output (same
            behavior as :func:`yesno`). Defaults to ``False``.

    Returns:
        str: ``'No'`` or ``'Yes'``, or ``''`` if the value is empty.
    """
    ...

def phone_number_part(number: Any, part: Any, country: Any = ...) -> Any:
    """
    Return a specific segment of a phone number's national format.

    Splits the nationally formatted phone number on non-digit separators and
    returns the segment at the given zero-based index.

    Args:
        number (str): The phone number to parse.
        part (int): The zero-based index of the segment to return
            (e.g. ``0`` for area code, ``1`` for exchange, ``2`` for
            subscriber number).
        country (str, optional): An ISO 3166-1 alpha-2 country code used
            to format the number. Defaults to the result of
            :func:`get_country`.

    Returns:
        str: The requested segment, or an empty string if parsing fails or
            the index is out of range.
    """
    ...

def log(the_message: Any, priority: Any = ...) -> Any:
    """
    Log a message to the server log, the browser console, or the user's screen.

    Args:
        the_message (str): The message to log.
        priority (str, optional): Destination and style. Use ``'log'`` for
            the server log, ``'console'`` for the browser console,
            ``'javascript'`` to run the message as JavaScript, or a
            Bootstrap alert level (``'success'``, ``'info'``, ``'danger'``,
            etc.) to show a popup notification. Defaults to ``'log'``.
    """
    ...

def encode_name(var: Any) -> Any:
    """
    Return the base64-encoded form of a Python variable name.

    Used internally to represent variable names as HTML input element names.

    Args:
        var (str): The Python variable name to encode.

    Returns:
        str: The base64-encoded variable name (without padding ``=`` characters).
    """
    ...

def decode_name(var: Any) -> Any:
    """
    Return the plain-text Python variable name from a base64-encoded form.

    The inverse of :func:`encode_name`.

    Args:
        var (str): A base64-encoded variable name.

    Returns:
        str: The decoded Python variable name.
    """
    ...

def interview_list(
    exclude_invalid: Any = ...,
    action: Any = ...,
    filename: Any = ...,
    session: Any = ...,
    user_id: Any = ...,
    query: Any = ...,
    include_dict: Any = ...,
    delete_shared: Any = ...,
    next_id: Any = ...,
) -> Any:
    """
    Return information about interview sessions, or perform bulk session operations.

    If the current user is logged in, returns a paginated list of interview
    session dictionaries. Can also delete sessions.

    Args:
        exclude_invalid (bool, optional): If ``True``, omit sessions where
            the interview could not be loaded or decrypted. Defaults to
            ``True``.
        action (str, optional): Pass ``'delete_all'`` to delete matching
            sessions (returns count deleted), or ``'delete'`` to delete a
            single session specified by ``filename`` and ``session``.
        filename (str, optional): Limit results to sessions of this
            interview filename.
        session (str, optional): Limit results to this session ID.
        user_id (int or str, optional): User ID to filter by, or ``'all'``
            for all users. Defaults to the current user.
        query: An optional query expression for complex filtering.
        include_dict (bool, optional): If ``True``, include the session
            dictionary in the results. Defaults to ``True``.
        delete_shared (bool, optional): When deleting, also delete shared
            sessions. Defaults to ``False``.
        next_id (str, optional): Pagination token from a previous call.

    Returns:
        tuple or int or None: A ``(list, next_id)`` tuple for listing, an
            integer when deleting, or ``None`` if the user is not logged in.
    """
    ...

def interview_menu(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return the list of available interviews shown at the ``/list`` page.

    Returns:
        list: A list of dictionaries, each describing an interview with
            keys such as ``title``, ``filename``, ``link``, ``tags``,
            and ``metadata``.
    """
    ...

def server_capabilities() -> Any:
    """
    Return a dictionary of boolean flags indicating what the server supports.

    Keys include ``'sms'``, ``'fax'``, ``'google_login'``, ``'facebook_login'``,
    ``'auth0_login'``, ``'keycloak_login'``, ``'authentik_login'``,
    ``'azure_login'``, ``'phone_login'``, ``'voicerss'``, ``'s3'``,
    ``'azure'``, ``'github'``, ``'pypi'``, ``'googledrive'``, and
    ``'google_maps'``.

    Returns:
        dict: A dictionary mapping capability names to True/False values.
    """
    ...

def session_tags() -> Any:
    """
    Return the set of tags associated with the current interview session.

    The tags are initialized from the ``tags`` list in any ``metadata`` blocks
    and can be modified using the returned set object.

    Returns:
        DATagsSet: A set-like object containing the current session tags.
    """
    ...

def get_chat_log(utc: Any = ..., timezone: Any = ...) -> Any:
    """
    Return the messages in the chat log of the current interview session.

    Args:
        utc (bool, optional): If True, return times in UTC. Defaults to False.
        timezone (str, optional): Timezone name to use for timestamps (e.g.,
            ``'America/New_York'``). Defaults to None.

    Returns:
        list: A list of chat messages for the current interview session.
    """
    ...

def get_user_list(include_inactive: Any = ..., next_id: Any = ...) -> Any:
    """
    Return a paginated list of registered users on the server.

    Requires ``admin``, ``advocate``, or the ``access_user_info`` permission.

    Args:
        include_inactive (bool, optional): If ``True``, include inactive
            users in the results. Defaults to ``False``.
        next_id (str, optional): Pagination token from a previous call.

    Returns:
        tuple or None: A ``(list, next_id)`` tuple where the list contains
            user-info dictionaries, or ``None`` if the user is not logged in.
    """
    ...

def get_user_info(user_id: Any = ..., email: Any = ...) -> Any:
    """
    Return profile information for a user.

    With no arguments, returns information about the currently logged-in
    user.  To look up another user, provide their ``user_id`` or ``email``.
    Requires the user to be logged in; admin/advocate or ``access_user_info``
    permission is required to look up other users.

    Args:
        user_id (int, optional): The user ID of the user to look up.
        email (str, optional): The e-mail address of the user to look up.

    Returns:
        dict or None: A dictionary of user profile information, or ``None``
            if no user is found.
    """
    ...

def set_user_info(**kwargs: Any) -> Any:
    """
    Write information to a user's profile.

    Updates profile fields for the current user, or for another user when
    ``user_id`` or ``email`` is provided.  Accepted keyword parameters
    include ``first_name``, ``last_name``, ``country``, ``language``,
    ``organization``, ``timezone``, ``password``, ``active``,
    ``privileges``, and others.  Requires the user to be logged in.

    Args:
        **kwargs: Profile fields to update.  Use ``user_id`` or ``email``
            to target a specific user.
    """
    ...

def get_user_secret(username: Any, password: Any) -> Any:
    """
    Return the decryption key for a user account if the credentials are valid.

    Used to obtain the encryption key required for :func:`get_session_variables`
    and :func:`set_session_variables` when the target interview uses
    server-side encryption.

    Args:
        username (str): The user's e-mail address.
        password (str): The user's password.

    Returns:
        str or None: The decryption key string if the credentials are valid,
            otherwise ``None``.
    """
    ...

def create_user(email: Any, password: Any, privileges: Any = ..., info: Any = ...) -> Any:
    """
    Create a new user account on the server.

    Requires ``admin`` privileges or the ``create_user`` permission.

    Args:
        email (str): The e-mail address for the new account.
        password (str): The password for the new account.
        privileges (str or list, optional): A privilege name or list of
            privilege names to assign to the new user.
        info (dict, optional): Additional profile information such as
            ``first_name``, ``last_name``, ``country``, etc.

    Returns:
        int: The user ID of the newly created account.
    """
    ...

def invite_user(email_address: Any, privilege: Any = ..., send: Any = ...) -> Any:
    """
    Create an invitation for a user to register an account.

    Generates a registration token for the given e-mail address.  Requires
    ``admin`` privileges or the ``create_user`` permission.

    Args:
        email_address (str): The e-mail address to invite.
        privilege (str, optional): A privilege to assign when the user
            registers. Defaults to the ordinary user privilege.
        send (bool, optional): If ``True`` (default), sends an invitation
            e-mail and returns ``None``.  If ``False``, returns the
            registration URL instead.

    Returns:
        str or None: The registration URL when ``send=False``, otherwise
            ``None``.
    """
    ...

def create_session(yaml_filename: Any, secret: Any = ..., url_args: Any = ...) -> Any:
    """
    Create a new interview session and return its session ID.

    Args:
        yaml_filename (str): The interview filename (e.g.
            ``'docassemble.demo:data/questions/questions.yml'``).
        secret (str, optional): The encryption key for the session. If
            not provided, the current user's key is used.
        url_args (dict, optional): URL arguments to make available in
            the new session via ``url_args``.

    Returns:
        str: The session ID of the newly created session.
    """
    ...

def get_session_variables(yaml_filename: Any, session_id: Any, secret: Any = ..., simplify: Any = ...) -> Any:
    """
    Return the interview dictionary for the specified session.

    Cannot be used to retrieve variables from the current session.

    Args:
        yaml_filename (str): The interview filename.
        session_id (str): The session ID.
        secret (str, optional): The encryption key for decrypting the
            session. Uses the current user's key if not provided.
        simplify (bool, optional): If ``True``, returns a simplified
            JSON-serializable dictionary. Defaults to ``True``.

    Returns:
        dict: The interview session dictionary.
    """
    ...

def set_session_variables(
    yaml_filename: Any,
    session_id: Any,
    variables: Any,
    secret: Any = ...,
    question_name: Any = ...,
    overwrite: Any = ...,
    process_objects: Any = ...,
    delete: Any = ...,
) -> Any:
    """
    Set variables in the interview dictionary of another session.

    Cannot be used to modify the current session.

    Args:
        yaml_filename (str): The interview filename.
        session_id (str): The session ID.
        variables (dict): A dictionary mapping variable name strings to
            their new values.
        secret (str, optional): The encryption key for the session.
        question_name (str, optional): The ID of a mandatory question to
            mark as answered.
        overwrite (bool, optional): If ``True``, overwrites the previous
            step instead of creating a new one. Defaults to ``False``.
        process_objects (bool, optional): If ``True``, treats the
            dictionary as a serializable representation of docassemble
            objects. Defaults to ``False``.
        delete (str or list, optional): Variable name(s) to undefine in
            the session.
    """
    ...

def go_back_in_session(yaml_filename: Any, session_id: Any, secret: Any = ...) -> Any:
    """
    Go back one step in a different interview session.

    Has the same effect as the user clicking the Back button in that session.
    Cannot be used on the current session.

    Args:
        yaml_filename (str): The interview filename.
        session_id (str): The session ID.
        secret (str, optional): The encryption key for the session.
    """
    ...

def manage_privileges(*pargs: Any) -> Any:
    """
    List, add, remove, or inspect privilege types on the system.

    Requires ``admin`` privileges or a custom privilege with the appropriate
    permissions.

    Args:
        *pargs: The first argument is the command (``'list'``, ``'add'``,
            ``'remove'``, or ``'inspect'``).  ``'add'`` and ``'remove'``
            take one or more privilege name strings as additional arguments.
            ``'inspect'`` takes a single privilege name.

    Returns:
        list or bool or None: The list of privileges for ``'list'``,
            permission details for ``'inspect'``, ``True`` for successful
            ``'add'``/``'remove'``, or ``None`` if not authenticated.
    """
    ...

def redact(text: Any) -> Any:
    """
    Return a redacted version of the text for use in documents.

    Replaces the text with a redaction mark unless redaction has been
    disabled for the current document (e.g., via ``redact: False``).

    Args:
        text (str): The text to potentially redact.

    Returns:
        str: The original text if redaction is disabled, or a redacted
            version (masking characters appropriate for the output format)
            if redaction is enabled.
    """
    ...

def forget_result_of(*pargs: Any) -> Any:
    """
    Reset the result of one or more blocks so they will run again.

    Used to re-ask questions with embedded blocks, or to re-run mandatory
    code blocks, by clearing the record of whether those blocks have been
    completed.

    Args:
        *pargs: The ``id`` strings of the blocks whose results should be
            forgotten.
    """
    ...

def re_run_logic() -> Any:
    """
    Stop execution and re-evaluate all initial and mandatory blocks from the beginning.

    Raises a ``ForcedReRun`` exception so that docassemble restarts the
    evaluation of interview logic.  Useful after making variable changes that
    should cause earlier blocks to run again.  Take care to avoid infinite
    loops.
    """
    ...

def reconsider(*pargs: Any, evaluate: Any = ...) -> Any:
    """
    Undefine and re-evaluate one or more variables, ensuring fresh values.

    Each variable is undefined and then immediately re-sought.  A variable
    is only reconsidered once per page load, even if called multiple times.

    Args:
        *pargs: Variable name strings to reconsider.
        evaluate (bool, optional): If ``True``, resolves alias variable
            names to their intrinsic names before reconsidering. Defaults
            to ``False``.
    """
    ...

def get_question_data(yaml_filename: Any, session_id: Any, secret: Any = ...) -> Any:
    """
    Return data about the current question for the specified interview session.

    Cannot be used on the current session.

    Args:
        yaml_filename (str): The interview filename.
        session_id (str): The session ID.
        secret (str, optional): The encryption key for decrypting the
            session. Uses the current user's key if not provided.

    Returns:
        dict: A dictionary containing data about the current question.
    """
    ...

def set_save_status(status: Any) -> Any:
    """
    Control whether the current interview logic processing creates a new step.

    Args:
        status (str): One of ``'new'`` (create a new step, the default),
            ``'overwrite'`` (overwrite the current step), or ``'ignore'``
            (do not save a new step at all).
    """
    ...

def single_to_double_newlines(text: Any) -> Any:
    """
    Convert single newlines to double newlines so each line break becomes a paragraph break.

    Useful when user-supplied text uses single newlines as paragraph
    separators, but the Markdown renderer requires double newlines.

    Args:
        text (str): The text to convert.

    Returns:
        str: The text with each sequence of newline characters replaced by
            two newlines.
    """
    ...

def verbatim(text: Any) -> Any:
    """
    Return the text with special formatting characters escaped for the current output context.

    Prevents Markdown, HTML, or LaTeX characters in user-supplied input from
    being interpreted as formatting codes when rendered on screen or in a
    document.

    Args:
        text (str): The text to escape.

    Returns:
        str: The text with formatting characters escaped appropriately for
            the current output context (Markdown, HTML, DOCX, or LaTeX).
    """
    ...

add_separators: Any

def store_variables_snapshot(
    data: Any = ..., include_internal: Any = ..., key: Any = ..., persistent: Any = ...
) -> Any:
    """
    Store a snapshot of the interview answers in unencrypted JSON format.

    Writes the current interview variables (or provided ``data``) to the
    database in plain JSON so they can be retrieved later without the user's
    encryption key.

    Args:
        data (optional): Data to store instead of the current interview
            variables. Defaults to ``None`` (uses current interview
            variables).
        include_internal (bool, optional): If ``True``, includes
            ``_internal`` variables in the snapshot. Defaults to ``False``.
        key (str, optional): A tag string to associate with the snapshot.
            Defaults to ``None``.
        persistent (bool, optional): If ``True``, the snapshot persists
            after the session ends. Defaults to ``False``.
    """
    ...

def update_terms(dictionary: Any, auto: Any = ..., language: Any = ...) -> Any:
    """
    Define or override interview-wide terms or auto terms programmatically.

    Args:
        dictionary (dict or list): A dictionary mapping term strings to their
            definitions, or a list of single-key dictionaries.
        auto (bool, optional): If True, update ``auto terms`` instead of
            ``terms``. Defaults to False.
        language (str, optional): The language code for which to set the terms.
            Use ``'*'`` for the default language. Defaults to ``'*'``.
    """
    ...

def set_variables(variables: Any, process_objects: Any = ...) -> Any:
    """
    Update the current interview answers using a dictionary of variable names and values.

    Similar to calling :func:`define` repeatedly, but accepts a dictionary.

    Args:
        variables (dict): A dictionary mapping variable name strings to
            their new values.
        process_objects (bool, optional): If ``True``, converts the
            dictionary from docassemble's serializable object representation
            (e.g., from ``.as_serializable()``) into actual Python objects.
            Defaults to ``False``.
    """
    ...

def language_name(language_code: Any) -> Any:
    """
    Return the full name of a language given its ISO-639-1 or ISO-639-3 code.

    The language name is passed through the ``word()`` function for translation.
    If the language cannot be found, the original code is returned (also via
    ``word()``).

    Args:
        language_code (str): A two-letter ISO-639-1 code (e.g., ``'en'``) or
            three-letter ISO-639-3 code (e.g., ``'eng'``).

    Returns:
        str: The full name of the language (e.g., ``'English'``).
    """
    ...

def run_action_in_session(
    yaml_filename: Any,
    session_id: Any,
    action: Any,
    arguments: Any = ...,
    secret: Any = ...,
    persistent: Any = ...,
    overwrite: Any = ...,
    read_only: Any = ...,
) -> Any:
    """
    Run an action in a different interview session.

    Cannot be used on the current session.

    Args:
        yaml_filename (str): The interview filename.
        session_id (str): The session ID of the target session.
        action (str): The name of the action (event) to run.
        arguments (dict, optional): Arguments to pass to the action.
        secret (str, optional): The encryption key for the session.
        persistent (bool, optional): If ``True``, the action can ask
            questions. Defaults to ``False``.
        overwrite (bool, optional): If ``True``, overwrites the previous
            step. Defaults to ``False``.
        read_only (bool, optional): If ``True``, the session is not saved
            after the action. Defaults to ``False``.

    Returns:
        bool: ``True`` on success.

    Raises:
        DAError: If the action fails or targets the current session.
    """
    ...
