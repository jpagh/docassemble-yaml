from __future__ import annotations

from typing import Any

"""Generated fallback stub for docassemble.base.util."""

def alpha(*args: Any, **kwargs: Any) -> Any: ...
def roman(*args: Any, **kwargs: Any) -> Any: ...
def item_label(*args: Any, **kwargs: Any) -> Any: ...

ordinal: Any

ordinal_number: Any

comma_list: Any

def word(*args: Any, **kwargs: Any) -> Any: ...
def get_language(*args: Any, **kwargs: Any) -> Any: ...
def set_language(*args: Any, **kwargs: Any) -> Any: ...
def get_dialect(*args: Any, **kwargs: Any) -> Any: ...
def get_voice(*args: Any, **kwargs: Any) -> Any: ...
def set_country(*args: Any, **kwargs: Any) -> Any: ...
def get_country(*args: Any, **kwargs: Any) -> Any: ...
def get_locale(*args: Any, **kwargs: Any) -> Any: ...
def set_locale(*args: Any, **kwargs: Any) -> Any: ...
def update_locale(*args: Any, **kwargs: Any) -> Any: ...

comma_and_list: Any

def need(*args: Any, **kwargs: Any) -> Any: ...

nice_number: Any

quantity_noun: Any

currency_symbol: Any

verb_past: Any

verb_present: Any

noun_plural: Any

noun_singular: Any

indefinite_article: Any

capitalize: Any

def space_to_underscore(*args: Any, **kwargs: Any) -> Any: ...
def force_ask(*args: Any, **kwargs: Any) -> Any: ...
def force_gather(*args: Any, **kwargs: Any) -> Any: ...

period_list: Any

name_suffix: Any

currency: Any

def static_image(*args: Any, **kwargs: Any) -> Any: ...

title_case: Any

def url_of(*args: Any, **kwargs: Any) -> Any: ...
def process_action(*args: Any, **kwargs: Any) -> Any: ...
def url_action(*args: Any, **kwargs: Any) -> Any: ...
def get_info(*args: Any, **kwargs: Any) -> Any: ...
def set_info(*args: Any, **kwargs: Any) -> Any: ...
def get_config(*args: Any, **kwargs: Any) -> Any: ...
def prevent_going_back(*args: Any, **kwargs: Any) -> Any: ...
def qr_code(*args: Any, **kwargs: Any) -> Any: ...
def action_menu_item(*args: Any, **kwargs: Any) -> Any: ...
def from_b64_json(*args: Any, **kwargs: Any) -> Any: ...
def defined(*args: Any, **kwargs: Any) -> Any: ...
def define(*args: Any, **kwargs: Any) -> Any: ...
def value(*args: Any, **kwargs: Any) -> Any: ...
def message(*args: Any, **kwargs: Any) -> Any: ...
def response(*args: Any, **kwargs: Any) -> Any: ...
def json_response(*args: Any, **kwargs: Any) -> Any: ...
def command(*args: Any, **kwargs: Any) -> Any: ...
def single_paragraph(*args: Any, **kwargs: Any) -> Any: ...
def quote_paragraphs(*args: Any, **kwargs: Any) -> Any: ...
def location_returned(*args: Any, **kwargs: Any) -> Any: ...
def location_known(*args: Any, **kwargs: Any) -> Any: ...
def user_lat_lon(*args: Any, **kwargs: Any) -> Any: ...
def interview_url(*args: Any, **kwargs: Any) -> Any: ...
def interview_url_action(*args: Any, **kwargs: Any) -> Any: ...
def interview_url_as_qr(*args: Any, **kwargs: Any) -> Any: ...
def interview_url_action_as_qr(*args: Any, **kwargs: Any) -> Any: ...

class LatitudeLongitude(DAObject):
    """
    A GPS coordinate obtained from the user's browser.

    Attributes:
        gathered (bool): True once the browser has responded with a location
            or an error.
        known (bool): True if a valid latitude and longitude were obtained.
        latitude (float): Latitude in decimal degrees (set when known).
        longitude (float): Longitude in decimal degrees (set when known).
        error (str): Browser error message (set when the location is
            unavailable).
        description (str): String representation of the location.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def status(self) -> Any:
        """
        Return True if the browser should be asked for the location; False otherwise.

        Returns:
            bool: True if a geolocation request should be sent; False if the
                location has already been gathered or returned.
        """
        ...
    def _set_to_current(self) -> Any: ...
    def __str__(self) -> Any: ...

class RoleChangeTracker(DAObject):
    """
    Tracks role changes in a multi-user interview to prevent duplicate notifications.

    Stores the last role for which a notification was sent and skips sending
    emails when the required role has not changed.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _update(self, target_role: Any) -> Any:
        """
        When a notification is delivered about a necessary change in the
        active role of the interviewee, this function is called with
        the name of the new role.  This prevents the send_email()
        function from sending duplicative notifications.
        """
        ...
    def send_email(self, roles_needed: Any, **kwargs: Any) -> Any:
        """
        Send a role-change notification email if needed.

        Args:
            roles_needed (list[str]): Role names that are now required for the
                interview to proceed.
            **kwargs: Each keyword argument is a role name mapping to a dict
                with ``'to'`` (recipient) and ``'email'`` (DATemplate) keys.
                A ``'config'`` key may specify the email configuration to use.

        Returns:
            bool: True if an email was successfully sent; False if no email
                was necessary or sending failed.
        """
        ...

class Name(DAObject):
    """
    Base class for a person's name, backed by a single ``text`` attribute.

    Attributes:
        text (str): The full name as a single string.
    """
    def full(self, **kwargs: Any) -> Any:
        """
        Return the full name.

        Returns:
            str: The ``text`` attribute of the name.
        """
        ...
    def familiar(self) -> Any:
        """
        Return the familiar (first) name.

        Returns:
            str: The familiar form of the name.
        """
        ...
    def firstlast(self) -> Any:
        """
        Return the name in first-last order (compatibility method).

        Returns:
            str: The name text.
        """
        ...
    def lastfirst(self) -> Any:
        """
        Return the name in last-first order (compatibility method).

        Returns:
            str: The name text.
        """
        ...
    def middle_initial(self, with_period: Any = ...) -> Any:
        """
        Return the middle initial (compatibility method; always empty for this class).

        Returns:
            str: Empty string.
        """
        ...
    def defined(self) -> Any:
        """
        Return True if the name has been defined.

        Returns:
            bool: True if the ``text`` attribute exists; False otherwise.
        """
        ...
    def __str__(self) -> Any: ...

class IndividualName(Name):
    """
    The name of an Individual, stored as separate parts.

    Attributes:
        uses_parts (bool): If True (the default), the name is assembled from
            ``first``, ``middle``, ``last``, ``suffix``, etc. If False, a
            single ``text`` attribute is used instead.
        first (str): First name.
        middle (str): Middle name (optional).
        last (str): Last name.
        suffix (str): Name suffix such as ``'Jr.'`` (optional).
        paternal_surname (str): Paternal surname (alternative to ``last``).
        maternal_surname (str): Maternal surname (optional).
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def defined(self) -> Any:
        """
        Return True if the name has been defined.

        Returns:
            bool: True if ``first`` (or ``text`` when ``uses_parts`` is False)
                has been set.
        """
        ...
    def familiar(self) -> Any:
        """
        Return the familiar (first) name.

        Returns:
            str: First name, or the full name when ``uses_parts`` is False.
        """
        ...
    def full(self, middle: Any = ..., use_suffix: Any = ...) -> Any:
        """
        Return the full name assembled from its parts.

        Args:
            middle (str, bool, or None): Controls middle-name inclusion.
                ``'initial'`` (default) includes the middle initial;
                ``True`` includes the full middle name; ``False`` or ``None``
                omits it.
            use_suffix (bool): If True (default), append the suffix when
                present.

        Returns:
            str: Full name string.
        """
        ...
    def firstlast(self) -> Any:
        """
        Return the name in "First Last" format.

        Returns:
            str: First and last name separated by a space.
        """
        ...
    def lastfirst(self) -> Any:
        """
        Return the name in "Last, First Middle" format.

        Returns:
            str: Last name, comma, first name, and optional middle initial and
                suffix.
        """
        ...
    def middle_initial(self, with_period: Any = ...) -> Any:
        """
        Return the middle initial.

        Args:
            with_period (bool): If True (default), append a period after the
                initial.

        Returns:
            str: Middle initial (e.g. ``'A.'``), or an empty string if there
                is no middle name.
        """
        ...

class Address(DAObject):
    """
    A geographic address with geocoding support.

    Attributes:
        address (str): Street address line (e.g. ``'123 Main St'``).
        unit (str): Unit, apartment, or suite number (optional).
        city (str): City name.
        state (str): State or province code.
        zip (str): ZIP or postal code.
        country (str): ISO 3166-1 alpha-2 country code (optional).
        location (LatitudeLongitude): GPS coordinates for the address.
        city_only (bool): If True, only city-level address fields are used.
        norm (Address): Normalized short-format address returned by the
            geocoder (set after geocoding).
        norm_long (Address): Normalized long-format address returned by the
            geocoder (set after geocoding).
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def on_one_line(
        self, include_unit: Any = ..., omit_default_country: Any = ..., language: Any = ..., show_country: Any = ...
    ) -> Any:
        """
        Return the address as a single line of text.

        Args:
            include_unit (bool): If True (default), include the unit number.
            omit_default_country (bool): If True (default), omit the country
                when it matches the interview's default country.
            language (str or None): Language code for localized unit labels.
            show_country (bool or None): If True, always show the country; if
                False, never show it; if None, apply the ``omit_default_country``
                logic.

        Returns:
            str: Address on a single line.
        """
        ...
    def _map_info(self) -> Any: ...
    def was_geocoded(self) -> Any:
        """
        Return True if geocoding has been attempted.

        Returns:
            bool: True if geocoding was performed; False otherwise.
        """
        ...
    def was_geocoded_successfully(self) -> Any:
        """
        Return True if geocoding was performed and succeeded.

        Returns:
            bool: True if geocoding was performed successfully; False
                otherwise.
        """
        ...
    def get_geocode_response(self) -> Any:
        """
        Return the raw response data from the geocoding service.

        Returns:
            list or dict: Raw geocoder response data, or an empty list if
                geocoding has not been performed.
        """
        ...
    def geolocate(self, address: Any = ..., reset: Any = ...) -> Any:
        """This exists for backward compatibility only. Use .geocode()."""
        ...
    def geocode(self, address: Any = ..., reset: Any = ...) -> Any:
        """
        Geocode the address to obtain latitude, longitude, and normalized fields.

        Args:
            address (str or None): If provided, geocode this string instead of
                assembling the address from the object's own fields.
            reset (bool): If True, clear any previous geocoding results before
                geocoding.

        Returns:
            bool: True if geocoding succeeded; False otherwise.
        """
        ...
    def normalize(self, long_format: Any = ...) -> Any: ...
    def reset_geolocation(self) -> Any:
        """This exists for backward compatibility only. Use .reset_geocoding()."""
        ...
    def reset_geocoding(self) -> Any:
        """Clear all geocoding results so the address can be geocoded again."""
        ...
    def block(self, language: Any = ..., international: Any = ..., show_country: Any = ...) -> Any:
        """
        Return the address formatted as a multi-line mailing block.

        Args:
            language (str or None): Language code for localized labels.
            international (bool): If True, use the i18n-address library for
                country-appropriate formatting.
            show_country (bool or None): If True, always include the country
                line; if False, never include it; if None, include it only
                when the country differs from the interview's default.

        Returns:
            str: Multi-line address block (lines joined with ``[NEWLINE]``
                markers in non-DOCX contexts).
        """
        ...
    def _get_country(self) -> Any: ...
    def formatted_unit(self, language: Any = ..., require: Any = ...) -> Any:
        """
        Return the unit number formatted as a display string.

        Args:
            language (str or None): Language code for the ``'Unit'``,
                ``'Floor'``, or ``'Room'`` label.
            require (bool): If True, trigger a question to collect the
                ``unit`` attribute when it is missing.

        Returns:
            str: Formatted unit string (e.g. ``'Unit 3B'``), or an empty
                string if no unit is defined.
        """
        ...
    def line_one(self, language: Any = ...) -> Any:
        """
        Return the first line of the address.

        Args:
            language (str or None): Language code for the unit label.

        Returns:
            str: Street address and optional unit, or an empty string for
                city-only addresses.
        """
        ...
    def line_two(self, language: Any = ...) -> Any:
        """
        Return the second line of the address.

        Returns:
            str: City, state, and ZIP/postal code.
        """
        ...

class City(Address):
    """An Address whose ``city_only`` flag is set to True from initialization."""
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...

class Event(DAObject):
    """
    An event with a city-level address and GPS location.

    Attributes:
        address (City): The city where the event takes place.
        location (LatitudeLongitude): GPS coordinates of the event.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __str__(self) -> Any: ...

class Person(DAObject):
    """
    A legal or natural person with a name, address, and location.

    Attributes:
        name (Name): The person's name.
        address (Address): The person's address.
        location (LatitudeLongitude): The person's GPS location.
        email (str): Email address.
        phone_number (str): Phone number.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _map_info(self) -> Any: ...
    def identified(self) -> Any:
        """
        Return True if the person's name has been defined.

        Returns:
            bool: True if the name text has been set; False otherwise.
        """
        ...
    def __setattr__(self, attrname: Any, the_value: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def pronoun_objective(self, **kwargs: Any) -> Any:
        """
        Return the objective pronoun for the person.

        Args:
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``person`` overrides the point-of-view (``'1'``, ``'1p'``,
                ``'2'``, ``'2p'``, or ``'3'``).

        Returns:
            str: Objective pronoun (e.g. ``'it'``, ``'you'``, ``'me'``).
        """
        ...
    def object_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive phrase using the variable name.

        Args:
            target (str): The thing being possessed.
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``person`` overrides the point-of-view.

        Returns:
            str: Possessive phrase (e.g. ``'your fish'`` or ``'my fish'``).
        """
        ...
    def is_are_you(self, **kwargs: Any) -> Any:
        """
        Return "are you" for the user, or "is [name]" for a third party.

        Args:
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``person`` overrides the point-of-view.

        Returns:
            str: Appropriate verb phrase (e.g. ``'are you'`` or ``'is Jane'``).
        """
        ...
    def address_block(self, language: Any = ..., international: Any = ..., show_country: Any = ...) -> Any:
        """
        Return the person's name and address formatted as a mailing block.

        Args:
            language (str or None): Language code for localized labels.
            international (bool): If True, use i18n-address formatting.
            show_country (bool): If True, include the country line.

        Returns:
            str: Name followed by the address block.
        """
        ...
    def sms_number(self, country: Any = ...) -> Any:
        """
        Return the person's phone number in E.164 format for SMS.

        Uses ``mobile_number`` if defined, otherwise ``phone_number``.

        Args:
            country (str or None): ISO 3166-1 alpha-2 country code used when
                parsing the number. Defaults to the address country or the
                interview default.

        Returns:
            str or None: E.164-formatted phone number, or None if parsing
                fails.
        """
        ...
    def subject(self, **kwargs: Any) -> Any: ...
    def facsimile_number(self, country: Any = ...) -> Any:
        """
        Return the person's fax number in E.164 format.

        Args:
            country (str or None): ISO 3166-1 alpha-2 country code used when
                parsing the number. Defaults to the address country or the
                interview default.

        Returns:
            str or None: E.164-formatted fax number, or None if parsing fails.
        """
        ...
    def email_address(self, include_name: Any = ...) -> Any:
        """
        Return the person's email address, optionally with display name.

        Args:
            include_name (bool or None): If True, include the name in
                ``"Name" <address>`` format. If None (default), include
                the name when it is defined.

        Returns:
            str: Formatted email address.
        """
        ...

class Thing(DAObject):
    """
    An object that has a name.

    Attributes:
        name (Name): The name of the thing.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __setattr__(self, attrname: Any, the_value: Any) -> Any: ...
    def __str__(self) -> Any: ...

class Individual(Person):
    """
    A natural person with a first/last name and biographical attributes.

    Attributes:
        name (IndividualName): The individual's name, stored as parts.
        birthdate (datetime.date or str): Date of birth.
        gender (str): Gender string (e.g. ``'male'``, ``'female'``).
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def familiar(self) -> Any:
        """
        Return the individual's familiar (first) name.

        Returns:
            str: First name, or full name when ``uses_parts`` is False.
        """
        ...
    def gather_family(self, tree: Any, up: Any = ..., down: Any = ...) -> Any: ...
    def identified(self) -> Any:
        """
        Return True if the individual's name has been defined.

        Returns:
            bool: True if ``name.first`` has been set; False otherwise.
        """
        ...
    def age_in_years(self, decimals: Any = ..., as_of: Any = ...) -> Any:
        """
        Return the individual's age in years.

        Args:
            decimals (bool): If True, return a float with fractional years;
                otherwise return an integer.
            as_of (datetime.date, str, or None): Calculate age as of this
                date instead of today.

        Returns:
            int or float: Age in years.
        """
        ...
    def age_in_months(self, decimals: Any = ..., as_of: Any = ...) -> Any:
        """
        Return the individual's age in months.

        Args:
            decimals (bool): If True, return a float with fractional months;
                otherwise return an integer.
            as_of (datetime.date, str, or None): Calculate age as of this
                date instead of today.

        Returns:
            int or float: Age in months.
        """
        ...
    def first_name_hint(self) -> Any:
        """
        Return the logged-in user's first name as a hint for the interview.

        Returns:
            str: First name from the user profile when this individual is the
                current user and they are authenticated; otherwise an empty
                string.
        """
        ...
    def last_name_hint(self) -> Any:
        """
        Return the logged-in user's last name as a hint for the interview.

        Returns:
            str: Last name from the user profile when this individual is the
                current user and they are authenticated; otherwise an empty
                string.
        """
        ...
    def salutation(self, **kwargs: Any) -> Any:
        """
        Return the appropriate salutation for the individual.

        Args:
            **kwargs: Forwarded to ``salutation()``; supports ``capitalize``.

        Returns:
            str: Salutation string (e.g. ``'Mr.'``, ``'Ms.'``).
        """
        ...
    def pronoun_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a gendered possessive phrase for the individual.

        Args:
            target (str): The thing being possessed (e.g. ``'fish'``).
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``thirdperson=True`` forces third-person regardless of
                point-of-view. ``person`` overrides the point-of-view.

        Returns:
            str: Possessive phrase (e.g. ``'her fish'``, ``'his fish'``,
                ``'your fish'``).
        """
        ...
    def pronoun(self, **kwargs: Any) -> Any:
        """
        Return the gendered objective pronoun for the individual.

        Args:
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``person`` overrides the point-of-view.

        Returns:
            str: Objective pronoun (e.g. ``'you'``, ``'her'``, ``'him'``).
        """
        ...
    def pronoun_objective(self, **kwargs: Any) -> Any:
        """
        Return the gendered objective pronoun (alias for :meth:`pronoun`).

        Returns:
            str: Objective pronoun.
        """
        ...
    def pronoun_subjective(self, **kwargs: Any) -> Any:
        """
        Return the gendered subjective pronoun for the individual.

        Args:
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``thirdperson=True`` forces third-person. ``person`` overrides
                the point-of-view.

        Returns:
            str: Subjective pronoun (e.g. ``'you'``, ``'she'``, ``'he'``).
        """
        ...
    def itself(self, **kwargs: Any) -> Any:
        """
        Return the appropriate reflexive pronoun for the individual.

        Args:
            **kwargs: Optional ``capitalize=True`` to capitalize the result.
                ``person`` overrides the point-of-view.

        Returns:
            str: Reflexive pronoun (e.g. ``'yourself'``, ``'herself'``,
                ``'himself'``).
        """
        ...
    def __setattr__(self, attrname: Any, the_value: Any) -> Any: ...
    def __str__(self) -> Any: ...

class ChildList(DAList):
    """A list of Individual objects representing children."""
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...

class FinancialList(DADict):
    """
    A dictionary of Value objects representing a set of currency amounts.

    Attributes:
        elements (dict): Maps item names (str) to Value objects.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def total(self) -> Any:
        """
        Return the total of all existing values in the list.

        Returns:
            Decimal: Sum of the ``value`` amounts for all items where
                ``exists`` is True.
        """
        ...
    def existing_items(self) -> Any:
        """
        Return a list of keys for items that exist in the financial list.

        Returns:
            list[str]: Sorted list of item names where ``exists`` is True.
        """
        ...
    def _new_item_init_callback(self) -> Any: ...
    def __str__(self) -> Any: ...

class PeriodicFinancialList(FinancialList):
    """
    A FinancialList where each entry has an associated payment period.

    Attributes:
        elements (dict): Maps item names (str) to PeriodicValue objects.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def total(self, period_to_use: Any = ...) -> Any:
        """
        Return the total of all periodic values normalized to a given period.

        Args:
            period_to_use (int or float): The period divisor for normalization.
                Defaults to 1 (returns the sum of ``value * period`` for each
                item).

        Returns:
            Decimal: Normalized total, or 0 if ``period_to_use`` is 0.
        """
        ...
    def _new_item_init_callback(self) -> Any: ...

class Income(PeriodicFinancialList):
    """A PeriodicFinancialList for recording a person's income sources."""

    ...

class Asset(FinancialList):
    """A FinancialList for recording a person's assets."""

    ...

class Expense(PeriodicFinancialList):
    """A PeriodicFinancialList for recording a person's expenses."""

    ...

class Value(DAObject):
    """
    A monetary value entry in a FinancialList.

    Attributes:
        exists (bool): True if the value is applicable (the item exists).
        value (Decimal or float): The monetary amount.
    """
    def amount(self) -> Any:
        """
        Return the value's amount, or 0 if it does not exist.

        Returns:
            Decimal: The amount, or ``Decimal(0)`` when ``exists`` is False.
        """
        ...
    def __str__(self) -> Any: ...
    def __float__(self) -> Any: ...
    def __int__(self) -> Any: ...
    def __le__(self, other: Any) -> Any: ...
    def __ge__(self, other: Any) -> Any: ...
    def __gt__(self, other: Any) -> Any: ...
    def __lt__(self, other: Any) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def __ne__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...

class PeriodicValue(Value):
    """
    A periodic monetary value entry in a PeriodicFinancialList.

    Attributes:
        period (int or float): Number of times per year this value occurs
            (e.g. 12 for monthly, 1 for annual).
        exists (bool): True if the value is applicable.
        value (Decimal or float): The amount per period.
    """
    def amount(self, period_to_use: Any = ...) -> Any:
        """
        Return the amount normalized to a given period.

        Args:
            period_to_use (int or float): The target period divisor. Use 12
                to get a monthly amount from an annual value, for example.
                Defaults to 1 (returns the raw per-period amount).

        Returns:
            Decimal: Normalized amount, or ``Decimal(0)`` when ``exists`` is
                False.
        """
        ...

class OfficeList(DAList):
    """A list of Address objects representing offices of an organization."""
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...

class Organization(Person):
    """
    A company or organization with offices and service areas.

    Attributes:
        office (OfficeList): List of the organization's office addresses.
        handles (list): Types of legal or service problems the organization
            handles.
        serves (list): Counties or geographic areas the organization serves.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def will_handle(self, problem: Any = ..., county: Any = ...) -> Any:
        """
        Return True if the organization handles the given problem and/or serves the given county.

        Args:
            problem (str or None): Problem type to check against ``handles``.
            county (str or None): County to check against ``serves``.

        Returns:
            bool: True if all provided criteria are met; False otherwise.
        """
        ...
    def _map_info(self) -> Any: ...

def objects_from_file(
    file_ref: Any,
    recursive: Any = ...,
    gathered: Any = ...,
    name: Any = ...,
    use_objects: Any = ...,
    package: Any = ...,
) -> Any:
    """
    Load and return objects from a YAML or JSON source file in the ``sources`` folder.

    Args:
        file_ref (DAFile, DAFileList, DAFileCollection, or int): Reference to
            the file containing the object data.
        recursive (bool): If True (default), recursively convert nested
            structures into docassemble objects.
        gathered (bool): If True (default), mark resulting collections as
            gathered. If False, reset gathered state so the interview can
            prompt for more items.
        name (str or None): Instance name to assign to the returned object.
            If None, the variable name at the call site is used.
        use_objects (bool): If True, convert dicts and lists into DADict and
            DAList objects instead of plain Python types.
        package (str or None): Package context for locating the file. Defaults
            to the current interview's package.

    Returns:
        DAObject, DAList, DADict, or a plain value: The deserialized object(s).

    Raises:
        DAError: If no file reference is provided.
        SystemError: If the referenced file cannot be found.
    """
    ...

def send_email(
    to: Any = ...,
    sender: Any = ...,
    reply_to: Any = ...,
    cc: Any = ...,
    bcc: Any = ...,
    body: Any = ...,
    html: Any = ...,
    subject: Any = ...,
    template: Any = ...,
    task: Any = ...,
    task_persistent: Any = ...,
    attachments: Any = ...,
    mailgun_variables: Any = ...,
    dry_run: Any = ...,
    config: Any = ...,
) -> Any:
    """
    Send an email message.

    Args:
        to (str, Person, DAEmailRecipient, list, or DAList): Primary
            recipient(s). Required.
        sender (str, Person, or DAEmailRecipient or None): Sender address.
            Defaults to the interview's configured sender.
        reply_to (str, Person, or DAEmailRecipient or None): Reply-to address.
        cc (str, Person, list, or None): Carbon-copy recipient(s).
        bcc (str, Person, list, or None): Blind carbon-copy recipient(s).
        body (str or None): Plain-text body. If omitted and ``template`` is
            provided, it is derived from the template.
        html (str or None): HTML body. If omitted, it is built from ``body``
            or ``template``.
        subject (str): Subject line. Defaults to the template subject if a
            ``template`` is provided.
        template (DATemplate or None): Template providing subject, body, and
            HTML.
        task (str or None): Interview task name to mark as performed on
            successful send.
        task_persistent (bool): If True, the task persists across sessions.
        attachments (list or None): File(s) to attach. Each item may be a
            DAFile, DAFileList, DAFileCollection, DAStaticFile, or a static
            file reference string.
        mailgun_variables (dict or None): Custom Mailgun variables to include
            in the X-Mailgun-Variables header.
        dry_run (bool): If True, do not send; only check whether sending would
            succeed.
        config (str or None): Email configuration name. Defaults to the
            interview's ``email config`` metadata or ``'default'``.

    Returns:
        bool: True if the email was sent (or would be sent in dry_run mode);
            False otherwise.
    """
    ...

def send_sms(
    to: Any = ...,
    body: Any = ...,
    template: Any = ...,
    task: Any = ...,
    task_persistent: Any = ...,
    attachments: Any = ...,
    config: Any = ...,
    dry_run: Any = ...,
) -> Any:
    """
    Send an SMS text message via Twilio.

    Args:
        to (str, list, or DAList): Recipient phone number(s).
        body (str or None): Plain-text message body. Required if ``template``
            is not provided.
        template (DATemplate or None): Template whose subject and content
            provide the message body.
        task (str or None): Interview task name to mark as performed on
            successful send.
        task_persistent (bool): If True, the task persists across sessions.
        attachments (list or None): File(s) to attach as MMS media.
        config (str): Twilio configuration name. Defaults to ``'default'``.
        dry_run (bool): If True, do not actually send; only return whether
            sending would succeed.

    Returns:
        bool: True if the message was sent successfully; False otherwise.
    """
    ...

def send_fax(fax_number: Any, file_object: Any, config: Any = ..., country: Any = ...) -> Any:
    """
    Send a fax via Twilio.

    Args:
        fax_number (str or Person): Recipient fax number or a Person object
            with a ``fax_number`` attribute.
        file_object (DAFile, DAFileList, or DAFileCollection): Document to
            fax. Multiple files in a DAFileList are concatenated into a single
            PDF before sending.
        config (str): Twilio configuration name. Defaults to ``'default'``.
        country (str or None): ISO 3166-1 alpha-2 country code for parsing
            the fax number.

    Returns:
        FaxStatus: Object representing the fax send operation.
    """
    ...

def map_of(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return markup that embeds a Google Map of the given objects.

    Args:
        *pargs: DAObject instances (or lists thereof) that implement
            ``_map_info()`` — typically Address or Person objects.
        **kwargs: Optional ``center`` keyword argument specifying the object
            to center the map on.

    Returns:
        str: A ``[MAP ...]`` markup string that the interview renderer converts
            to an embedded Google Map, or a localized ``'(Unable to display
            map)'`` string if no map data is available.
    """
    ...

def selections(*pargs: Any, **kwargs: Any) -> Any:
    """
    Build a list of choice dictionaries from DAObject instances for use in a multiple-choice field.

    Args:
        *pargs: One or more DAObject instances, DAList/DASet collections, or
            plain lists containing DAObjects to include as choices.
        **kwargs: Optional keyword arguments:
            - ``object_labeler`` (callable): Function that returns the display
              label for each object. Defaults to ``str``.
            - ``help_generator`` (callable): Function that returns help text
              for each object, or None to omit help.
            - ``image_generator`` (callable): Function that returns an image
              reference for each object, or None to omit images.
            - ``exclude``: Object(s) to exclude from the choices.
            - ``default``: Object(s) to mark as selected by default.

    Returns:
        list[dict]: List of choice dictionaries suitable for use as ``code``
            in a ``choices`` field.
    """
    ...

class BackgroundAction(DAObject):
    """
    Manages a long-running Celery background action from within an interview.

    On first access the background action is dispatched and the interview
    shows a wait screen; on subsequent accesses the result is returned once
    the action completes.

    Attributes:
        refresh_seconds (int): Seconds between wait-screen refresh polls.
            Defaults to 4.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def run(self, action: Any, **pargs: Any) -> Any: ...
    def initial_wait(self) -> Any: ...
    def wait(self) -> Any: ...
    def process_response(self, result: Any) -> Any: ...
    def on_failure(self, result: Any) -> Any: ...
    def running(self) -> Any: ...
    def ready(self) -> Any: ...

class DAObject:
    """
    Base class for all docassemble objects.

    DAObjects are special Python objects whose attributes can be defined
    interactively by docassemble interview questions. When code or a template
    refers to an undefined attribute of a DAObject, docassemble searches for
    a question or code block that can define it, rather than raising an
    AttributeError immediately.

    Every DAObject has an ``instanceName`` attribute that stores the variable
    name used when the object was created. This intrinsic name is used to
    find the appropriate question or code block when an attribute is undefined.

    Attributes:
        instanceName (str): The variable name of the object within the
            interview namespace (e.g., ``'client'`` or ``'client.address'``).
        has_nonrandom_instance_name (bool): True if the instance name was set
            explicitly; False if a random name was generated.
        attrList (list): A list of attribute names that have been set on this
            object.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Initialize the object by setting keyword arguments as attributes.

        This method is called by ``__init__`` after the instance name is
        established. Subclasses can override it to perform custom
        initialization while still calling ``super().init()``.

        Args:
            *pargs: Positional arguments (unused in base implementation).
            **kwargs: Each keyword argument is set as an attribute on the
                object.
        """
        ...
    @classmethod
    def using(cls, **kwargs: Any) -> Any:
        """
        Return a class-with-parameters object for use with DAList/DADict.

        This is used as an argument to ``object_type`` or
        ``appendObject()`` when you want the new objects to be initialized
        with specific keyword arguments.

        Args:
            **kwargs: Keyword arguments that will be passed to the ``init``
                method when new objects of this class are created.

        Returns:
            DAObjectPlusParameters: An object that bundles the class and the
                initialization parameters.
        """
        ...
    def __init__(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _set_instance_name_for_function(self) -> Any: ...
    def _set_instance_name_for_method(self) -> Any: ...
    def attr_name(self, attr: Any) -> Any:
        """
        Return the full variable name for an attribute.

        Useful when passing variable names (as strings) to functions like
        ``force_ask()`` and ``reconsider()``.

        Args:
            attr (str): The attribute name.

        Returns:
            str: The full dotted variable name, e.g. ``'person[3].birthdate'``.
        """
        ...
    def delattr(self, *pargs: Any) -> Any:
        """
        Delete one or more attributes, ignoring those that are not defined.

        Args:
            *pargs (str): Attribute names to delete.
        """
        ...
    def invalidate_attr(self, *pargs: Any) -> Any:
        """
        Invalidate one or more attributes, preserving their values as defaults.

        Like ``delattr()``, but the old value is remembered as the default
        when the interview asks the question again.

        Args:
            *pargs (str): Attribute names to invalidate.
        """
        ...
    def getattr_fresh(self, attr: Any) -> Any:
        """
        Recompute an attribute via reconsider() and return the fresh value.

        Should only be used on attributes that are defined by ``code`` blocks,
        not by questions posed to the user.

        Args:
            attr (str): The attribute name to recompute.

        Returns:
            The recomputed attribute value.
        """
        ...
    def is_peer_relation(self, target: Any, relationship_type: Any, tree: Any) -> Any: ...
    def is_relation(
        self, target: Any, relationship_type: Any, tree: Any, self_is: Any = ..., filter_by: Any = ...
    ) -> Any: ...
    def get_relation(
        self,
        relationship_type: Any,
        tree: Any,
        self_is: Any = ...,
        create: Any = ...,
        object_type: Any = ...,
        complete_attribute: Any = ...,
        rel_filter_by: Any = ...,
        filter_by: Any = ...,
        count: Any = ...,
    ) -> Any: ...
    def get_peer_relation(
        self,
        relationship_type: Any,
        tree: Any,
        create: Any = ...,
        object_type: Any = ...,
        complete_attribute: Any = ...,
        rel_filter_by: Any = ...,
        filter_by: Any = ...,
        count: Any = ...,
    ) -> Any: ...
    def set_peer_relationship(self, target: Any, relationship_type: Any, tree: Any, replace: Any = ...) -> Any: ...
    def set_relationship(
        self, target: Any, relationship_type: Any, self_is: Any, tree: Any, replace: Any = ...
    ) -> Any: ...
    def get_point_of_view(self) -> Any: ...
    def fix_instance_name(self, old_instance_name: Any, new_instance_name: Any) -> Any:
        """
        Replace the instance name prefix for this object and all sub-objects.

        Args:
            old_instance_name (str): The old prefix to replace.
            new_instance_name (str): The new prefix to use.
        """
        ...
    def set_instance_name(self, thename: Any) -> Any:
        """
        Set the instanceName, but only if it has not already been set explicitly.

        Args:
            thename (str): The desired instance name.
        """
        ...
    def set_random_instance_name(self) -> Any:
        """Set the instanceName attribute to a randomly generated value."""
        ...
    def copy_shallow(self, thename: Any) -> Any:
        """
        Return a shallow copy of the object with a new instance name.

        Sub-objects are shared references; modifying them in the copy will
        also modify them in the original.

        Args:
            thename (str): The instance name to assign to the new object.

        Returns:
            DAObject: A shallow copy of this object.
        """
        ...
    def copy_deep(self, thename: Any) -> Any:
        """
        Return a deep copy of the object with new instance names throughout.

        Sub-objects are fully copied and their instance names are updated to
        reflect their position within the new object hierarchy.

        Args:
            thename (str): The instance name to assign to the new object.

        Returns:
            DAObject: A deep copy of this object.
        """
        ...
    def _set_instance_name_recursively(self, thename: Any, matching: Any = ...) -> Any:
        """Sets the instanceName attribute, if it is not already set, and that of subobjects."""
        ...
    def _mark_as_gathered_recursively(self) -> Any: ...
    def _reset_gathered_recursively(self) -> Any: ...
    def _map_info(self) -> Any: ...
    def __getattr__(self, thename: Any) -> Any: ...
    def raise_undefined_attribute_error(self, thename: Any) -> Any:
        """
        Raise a DAAttributeError for the named attribute, as if the attribute were undefined.

        Useful when implementing ``@property`` getter/setter pairs that need
        to trigger docassemble's question-seeking behavior.

        Args:
            thename (str): The attribute name that is considered undefined.

        Raises:
            DAAttributeError: Always raised.
        """
        ...
    def object_name(self, **kwargs: Any) -> Any:
        """
        Return a human-readable name for the object based on its instance name.

        Converts dotted variable names into readable phrases. For example,
        ``case.plaintiff`` becomes ``"plaintiff in the case"``.

        Args:
            **kwargs: Accepts ``capitalize=True`` to capitalize the result.

        Returns:
            str: A human-readable name derived from the instance name.
        """
        ...
    def as_serializable(self) -> Any:
        """
        Return a simplified, serializable representation of the object.

        Objects are converted to Python dicts so that the result can be
        serialized to JSON or other formats. The conversion is not reversible.

        Returns:
            dict: A serializable dict representation of the object.
        """
        ...
    def possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive phrase appropriate to this object.

        Args:
            target (str): The noun to be possessed, e.g. ``'fish'``.
            **kwargs: Optional keyword arguments including ``capitalize``
                (bool) and ``person`` (str, one of ``'1'``, ``'2'``,
                ``'3'``, ``'1p'``, ``'2p'``).

        Returns:
            str: E.g. ``"your fish"`` if the object is the user, or
            ``"John Smith's fish"`` otherwise.
        """
        ...
    def object_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive phrase based on the instance name rather than the object's value.

        Args:
            target (str): The noun to be possessed, e.g. ``'fish'``.
            **kwargs: Optional keyword arguments including ``capitalize``
                (bool) and ``language`` (str).

        Returns:
            str: E.g. ``"client's fish"`` or ``"the latch of the front gate
            in the park"``.
        """
        ...
    def is_are_you(self, **kwargs: Any) -> Any:
        """
        Return "are you" if the object is the user, or "is <name>" otherwise.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"are you"`` or ``"is John Smith"``.
        """
        ...
    def yourself_or_name(self, **kwargs: Any) -> Any:
        """
        Return "yourself" if the object is the user, otherwise the object as a string.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: ``"yourself"`` when object is the user, or ``str(self)``
            otherwise.
        """
        ...
    def itself(self, **kwargs: Any) -> Any:
        """
        Return an appropriate reflexive pronoun for this object.

        Args:
            **kwargs: Accepts ``person`` (str, one of ``'1'``, ``'2'``,
                ``'1p'``, ``'2p'``) to force a particular person.

        Returns:
            str: ``"yourself"``, ``"itself"``, ``"myself"``, etc.
        """
        ...
    def is_user(self) -> Any:
        """Return True if this object is the current user, otherwise False."""
        ...
    def initializeAttribute(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Define an attribute as a newly initialized DAObject, if not already defined.

        The attribute will be created with an ``instanceName`` derived from
        this object's own ``instanceName``. If the attribute is already
        defined, this method has no effect and returns the existing attribute.

        Args:
            *pargs: First positional argument is the attribute name (str);
                second is the object class (or result of ``cls.using()``).
            **kwargs: Additional keyword arguments passed to the new object's
                ``init`` method.

        Returns:
            DAObject: The newly created (or already existing) attribute object.
        """
        ...
    def reInitializeAttribute(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Redefine an attribute as a newly initialized DAObject, overwriting any existing value.

        Like ``initializeAttribute()``, but overwrites the attribute even if
        it is already defined.

        Args:
            *pargs: First positional argument is the attribute name (str);
                second is the object class (or result of ``cls.using()``).
            **kwargs: Additional keyword arguments passed to the new object's
                ``init`` method.

        Returns:
            DAObject: The newly created attribute object.
        """
        ...
    def attribute_defined(self, name: Any) -> Any:
        """
        Return True if the named attribute is defined, otherwise False.

        Unlike accessing the attribute directly, this method does not trigger
        the question-seeking process.

        Args:
            name (str): The attribute name to check.

        Returns:
            bool: True if the attribute is defined.
        """
        ...
    def attr(self, name: Any) -> Any:
        """
        Return the value of the named attribute, or None if it is not defined.

        Unlike ``getattr()``, this method does not trigger the question-seeking
        process when the attribute is not defined.

        Args:
            name (str): The attribute name.

        Returns:
            The attribute value, or None if not defined.
        """
        ...
    def __str__(self) -> Any: ...
    def __dir__(self) -> Any: ...
    def pronoun_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive pronoun phrase appropriate for this object.

        Args:
            target (str): The noun to be possessed, e.g. ``'reason'``.
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"its reason"``, ``"your reason"``, or ``"my reason"``.
        """
        ...
    def pronoun(self, **kwargs: Any) -> Any:
        """
        Return an objective pronoun appropriate for this object.

        For a generic DAObject (not an Individual), this returns ``"it"``
        for the third person. Subclasses like Individual override this.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"it"``, ``"you"``, or ``"me"``.
        """
        ...
    def pronoun_objective(self, **kwargs: Any) -> Any:
        """
        Return an objective pronoun. Identical to ``pronoun()`` for DAObject.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"it"`` or ``"you"``.
        """
        ...
    def pronoun_subjective(self, **kwargs: Any) -> Any:
        """
        Return a subjective pronoun appropriate for this object.

        For a generic DAObject (not an Individual), this returns ``"it"``
        for the third person.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"it"``, ``"you"``, or ``"I"``.
        """
        ...
    def alternative(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a value that depends on the current value of a named attribute.

        Args:
            *pargs: First positional argument is the attribute name (str).
            **kwargs: Keys are possible attribute values; the corresponding
                value is returned when the attribute matches. Use ``_default``
                or ``default`` as a fallback key.

        Returns:
            The value associated with the current attribute value, or None
            if no match and no default.
        """
        ...
    def do_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return a present-tense do-question appropriate for this object.

        Args:
            the_verb (str): The infinitive verb, e.g. ``'eat'``.
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"do you eat"`` or ``"does John Smith eat"``.
        """
        ...
    def did_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return a past-tense did-question appropriate for this object.

        Args:
            the_verb (str): The infinitive verb, e.g. ``'eat'``.
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"did you eat"`` or ``"did John Smith eat"``.
        """
        ...
    def were_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Return a past-tense were/was question appropriate for this object.

        Args:
            the_target (str): The predicate, e.g. ``'married'``.
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"were you married"`` or ``"was John Smith married"``.
        """
        ...
    def have_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Return a present-perfect have/has question appropriate for this object.

        Args:
            the_target (str): The predicate, e.g. ``'signed'``.
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"have you signed"`` or ``"has John Smith signed"``.
        """
        ...
    def does_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated present-tense form of a verb.

        Args:
            the_verb (str): The infinitive verb, e.g. ``'eat'``.
            **kwargs: Accepts ``capitalize`` (bool), ``person`` (str), and
                ``past`` (bool) to use past tense instead.

        Returns:
            str: E.g. ``"eat"`` (second person) or ``"eats"`` (third person).
        """
        ...
    def did_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated past-tense form of a verb.

        Args:
            the_verb (str): The infinitive verb, e.g. ``'eat'``.
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"ate"`` or ``"ate"`` (conjugated for person).
        """
        ...
    def subjective_pronoun_or_name(self, **kwargs: Any) -> Any:
        """
        Return a subjective pronoun if the object is the user, or the object as a string.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"you"`` (second person) or ``"John Smith"``
            (third person).
        """
        ...
    def pronoun_or_name(self, **kwargs: Any) -> Any:
        """
        Return an objective pronoun if the object is the user, or the object as a string.

        Args:
            **kwargs: Accepts ``capitalize`` (bool) and ``person`` (str).

        Returns:
            str: E.g. ``"you"`` (second person) or ``"John Smith"``
            (third person).
        """
        ...
    def __setattr__(self, key: Any, the_value: Any) -> Any: ...
    def __le__(self, other: Any) -> Any: ...
    def __ge__(self, other: Any) -> Any: ...
    def __gt__(self, other: Any) -> Any: ...
    def __lt__(self, other: Any) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def __ne__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...

class DAList(DAObject):
    """
    A list that docassemble can populate through interview questions.

    DAList behaves like a Python list, but docassemble can ask questions to
    define items of the list. It supports an automatic gathering process
    controlled by attributes such as ``there_are_any`` and
    ``there_is_another``.

    Attributes:
        elements (list): The underlying Python list of items.
        gathered (bool): True when all items have been gathered.
        auto_gather (bool): If True (the default), the gathering process is
            triggered automatically. Set to False to control gathering
            manually.
        object_type: A DAObject subclass (or result of ``.using()``) used
            when creating new items via ``appendObject()``. Defaults to None.
        complete_attribute (str or None): An attribute that must be defined
            on each item before the item is considered complete during
            gathering.
        ask_number (bool): If True, docassemble will ask for the number of
            items before gathering them.
        minimum_number (int or None): Minimum number of items to gather.
        there_are_any (bool): Whether any items exist. Sought by the
            gathering process when the list is empty.
        there_is_another (bool): Whether there is another item to add. Sought
            repeatedly during gathering.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def initializeObject(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Create a new object at a given index in the list.

        Args:
            *pargs: First positional argument must be a non-negative integer
                index. An optional second positional argument is the class
                (or ``.using()`` result) to use for the new object. Falls
                back to ``object_type``, then ``new_object_type`` (when
                ``ask_object_type`` is True), then ``DAObject``.
            **kwargs: Additional keyword arguments are passed to the new
                object's constructor.

        Returns:
            DAObject: The newly created object stored at ``self[index]``.

        Raises:
            DAError: If the first argument is not a non-negative integer.
        """
        ...
    def set_object_type(self, object_type: Any) -> Any:
        """
        Set the object type used when creating new list items.

        Args:
            object_type: A class or ``.using()`` result to use when
                ``appendObject()`` creates new items.
        """
        ...
    def cancel_add_or_edit(self) -> Any: ...
    def gathered_and_complete(self) -> Any:
        """
        Ensure every item in the list is complete and return True.

        Resets ``gathered`` so the gathering process re-checks completeness,
        then calls ``gather()`` (or reads ``gathered`` for manual gathering).

        Returns:
            bool: Always True once all items are complete.
        """
        ...
    def item_name(self, item: Any) -> Any:
        """
        Return the variable name for a list item by its index.

        Args:
            item (int): The index of the item.

        Returns:
            str: Variable name such as ``'mylist[0]'``, suitable for use
                in ``force_ask()`` and similar functions.
        """
        ...
    def delitem(self, *pargs: Any) -> Any:
        """
        Delete items by index.

        Args:
            *pargs (int): Zero or more index numbers of items to delete.
                Indices that exceed the list length are silently ignored.
        """
        ...
    def copy(self) -> Any:
        """Returns a copy of the list."""
        ...
    def filter(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a new DAList containing only items matching the given attribute values.

        Args:
            *pargs: Optional first argument sets the instance name of the
                returned list; defaults to this list's instance name.
            **kwargs: Attribute name/value pairs used to filter items.
                Items where ``getattr(item, key) != val`` are excluded.

        Returns:
            DAList: A gathered copy containing only matching items.
        """
        ...
    def _trigger_gather(self) -> Any:
        """Triggers the gathering process."""
        ...
    def reset_gathered(self, recursive: Any = ..., only_if_empty: Any = ..., mark_incomplete: Any = ...) -> Any:
        """
        Reset the gathered state so the collection will be re-gathered.

        Args:
            recursive (bool): If True, also reset gathering on nested DAList
                and DADict objects within the collection. Defaults to False.
            only_if_empty (bool): If True, only reset if the collection is
                empty. Defaults to False.
            mark_incomplete (bool): If True, delete the ``complete_attribute``
                on each item so items are treated as incomplete. Defaults to
                False.
        """
        ...
    def has_been_gathered(self) -> Any:
        """
        Return True if the gathering process has completed.

        Returns:
            bool: True if the list has been gathered; False otherwise.
        """
        ...
    def pop(self, *pargs: Any) -> Any:
        """Remove an item the list and return it."""
        ...
    def item(self, index: Any) -> Any:
        """
        Return the item at the given index, or a blank DAEmpty if out of range.

        Args:
            index (int): Zero-based position of the item.

        Returns:
            object: The item at ``index``, or a ``DAEmpty`` instance.
        """
        ...
    def __add__(self, other: Any) -> Any: ...
    def __radd__(self, other: Any) -> Any: ...
    def index(self, *pargs: Any, **kwargs: Any) -> Any:
        """Returns the first index at which a given item may be found."""
        ...
    def clear(self) -> Any:
        """Removes all the items from the list."""
        ...
    def fix_instance_name(self, old_instance_name: Any, new_instance_name: Any) -> Any:
        """Substitutes a different instance name for the object and its subobjects."""
        ...
    def _set_instance_name_recursively(self, thename: Any, matching: Any = ...) -> Any:
        """Sets the instanceName attribute, if it is not already set, and that of subobjects."""
        ...
    def _mark_as_gathered_recursively(self) -> Any: ...
    def _reset_gathered_recursively(self) -> Any: ...
    def _reset_instance_names(self) -> Any: ...
    def sort(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Sort the list in place, trigger gathering first, and return self.

        Args:
            **kwargs: Keyword arguments passed to Python's ``sorted()``
                (e.g., ``key``, ``reverse``).

        Returns:
            DAList: This list object, for chaining.
        """
        ...
    def reverse(self, *pargs: Any, **kwargs: Any) -> Any:
        """Reverse the order of the elements of the list in place and returns the object."""
        ...
    def sort_elements(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Sort the list in place without triggering gathering, and return self.

        Args:
            **kwargs: Keyword arguments passed to Python's ``sorted()``
                (e.g., ``key``, ``reverse``).

        Returns:
            DAList: This list object, for chaining.
        """
        ...
    def appendObject(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Create a new object and append it to the list.

        Args:
            *pargs: An optional first positional argument specifies the class
                (or ``.using()`` result) for the new object. Falls back to
                ``object_type``, then ``new_object_type`` (when
                ``ask_object_type`` is True), then ``DAObject``.
            **kwargs: Additional keyword arguments passed to the new object's
                constructor.

        Returns:
            DAObject: The newly created object appended to the list.
        """
        ...
    def append(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Add one or more items to the end of the list.

        Args:
            *pargs: Items to append. DAObject items without a non-random
                instance name are renamed to match their position in this
                list.
            **kwargs: Pass ``set_instance_name=True`` to force renaming of
                DAObject items even if they already have a non-random name.
        """
        ...
    def remove(self, *pargs: Any) -> Any:
        """
        Remove items from the list by value.

        Args:
            *pargs: Values to remove. Items not found in the list are
                silently ignored. Sets ``there_are_any`` to False if the
                list becomes empty.
        """
        ...
    def _remove_items_by_number(self, *pargs: Any) -> Any:
        """Removes items from the list, by index number"""
        ...
    def insert(self, *pargs: Any) -> Any:
        """Inserts an item at the given position."""
        ...
    def count(self, item: Any) -> Any:
        """Returns the number of times item appears in the list."""
        ...
    def extend(self, the_list: Any) -> Any:
        """Adds each of the elements of the given list to the end of the list."""
        ...
    def first(self) -> Any:
        """Returns the first element of the list"""
        ...
    def last(self) -> Any:
        """Returns the last element of the list"""
        ...
    def is_user(self) -> Any:
        """Returns True if the list has one element and that element is the user, otherwise False."""
        ...
    def itself(self, **kwargs: Any) -> Any:
        """
        Returns "themselves" unless the list has only one element,
        in which case the method is called on the first element.
        """
        ...
    def do_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Given a verb like "eat," returns "do x eat" if there is
        more than one element. x is the string representation of the
        list. If there is only one element, the method is called on
        the first element of the list.
        """
        ...
    def did_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Given a verb like "eat," returns "did x eat" if there is
        more than one element. x is the string representation of the
        list. If there is only one element, the method is called on
        the first element of the list.
        """
        ...
    def were_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Given a target like "married", returns "were x married" if
        there is more than one element in the list. x is the string
        representation of the list. If there is only one element, the
        method is called on the first element.
        """
        ...
    def have_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Given a target like "married", returns "have x married" if
        there is more than one element in the list. x is the string
        representation of the list. If there is only one element, the
        method is called on the first element.
        """
        ...
    def does_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated present-tense form of a verb for the list.

        Args:
            the_verb (str): The base form of the verb (e.g., ``"sue"``).
            **kwargs: Accepts ``person`` (str), ``language`` (str), ``past``
                (bool), and ``present`` (bool) for tense control.

        Returns:
            str: Conjugated verb, e.g. "sues" for one plaintiff or "sue" for
                multiple plaintiffs.
        """
        ...
    def did_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated past-tense form of a verb for the collection.

        Args:
            the_verb (str): The base form of the verb (e.g., ``"sue"``).
            **kwargs: Accepts ``person`` (str) and ``language`` (str).

        Returns:
            str: Past-tense conjugated verb, e.g. "sued".
        """
        ...
    def as_singular_noun(self) -> Any:
        """
        Return the singular noun form derived from the list's instance name.

        E.g., ``case.plaintiff.child.as_singular_noun()`` returns ``"child"``
        regardless of how many children are in the list.

        Returns:
            str: Singular noun form of the trailing part of the instance name.
        """
        ...
    def possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive phrase using the list's noun form and the target.

        Args:
            target (str): The possessed noun phrase (e.g., ``"fish"``).
            **kwargs: Passed to ``possessify()``; may include ``language``.

        Returns:
            str: E.g., "plaintiff's fish" (one item) or "plaintiffs' fish"
                (multiple items).
        """
        ...
    def is_are_you(self, **kwargs: Any) -> Any:
        """
        Returns "are" followed by the list object reduced to text,
        but if the list has only one element, the method is called on
        that element instead.
        """
        ...
    def quantity_noun(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Returns the output of the quantity_noun() function using the number
        of elements in the list as the quantity.
        """
        ...
    def as_noun(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a singular or plural noun form for the list, derived from the instance name.

        Uses singular when the list has exactly one element, plural otherwise.
        E.g., ``case.plaintiff.child.as_noun()`` returns ``"child"`` or
        ``"children"`` as appropriate.

        Args:
            *pargs: If provided, the first argument overrides the noun (instead
                of using the instance name).
            **kwargs: Accepts ``plural`` (bool), ``singular`` (bool),
                ``article`` (bool), ``some`` (bool), ``this`` (bool),
                ``capitalize`` (bool), and ``language`` (str).

        Returns:
            str: Noun form with optional article.
        """
        ...
    def number(self) -> Any:
        """
        Return the number of elements in the list, triggering gathering if needed.

        Returns:
            int: Count of items in the list.
        """
        ...
    def gathering_started(self) -> Any:
        """
        Return True if any items have been gathered or ``there_are_any`` has been set.

        Returns:
            bool: True if gathering has started; False otherwise.
        """
        ...
    def number_gathered(self, if_started: Any = ...) -> Any:
        """
        Return the count of items gathered so far, without triggering gathering.

        Args:
            if_started (bool): If True, trigger gathering when gathering has
                not yet started. Defaults to False.

        Returns:
            int: Number of items currently in the collection.
        """
        ...
    def current_index(self) -> Any:
        """
        Return the index of the last item added, or 0 if the list is empty.

        Returns:
            int: Zero-based index of the last element, or 0 when empty.
        """
        ...
    def number_as_word(self, language: Any = ..., capitalize: Any = ...) -> Any:
        """
        Return the number of items spelled out as a word when ten or fewer.

        Args:
            language (str, optional): Language code for localization.
            capitalize (bool): If True, capitalize the result. Defaults to
                False.

        Returns:
            str: Spelled-out number (e.g., "three") for counts up to ten;
                numeral string otherwise.
        """
        ...
    def complete_elements(self, complete_attribute: Any = ...) -> Any:
        """
        Return a gathered DAList of only the complete items.

        An item is complete if ``str()`` succeeds on it and, when
        ``complete_attribute`` is set, each attribute named therein is
        defined.

        Args:
            complete_attribute (str or list, optional): Override the list's
                own ``complete_attribute`` setting.

        Returns:
            DAList: A new DAList with ``gathered=True`` containing only
                complete items.
        """
        ...
    def _complete_attributes(self, complete_attribute: Any = ...) -> Any: ...
    def _validate(self, item_object_type: Any, complete_attribute: Any) -> Any: ...
    def _allow_appending(self) -> Any: ...
    def _disallow_appending(self) -> Any: ...
    def gather(
        self, number: Any = ..., item_object_type: Any = ..., minimum: Any = ..., complete_attribute: Any = ...
    ) -> Any:
        """
        Trigger the gathering process for the list and return True.

        Runs the interview question loop that asks ``there_are_any``,
        creates items, and asks ``there_is_another`` until the list is
        complete. Called automatically when iterating over or measuring
        the list (unless ``auto_gather`` is False).

        Args:
            number (int, optional): Collect exactly this many items.
            item_object_type: Class to use when creating items; overrides
                ``object_type``.
            minimum (int, optional): Minimum number of items to collect.
            complete_attribute (str or list, optional): Attribute(s) that
                must be defined for an item to be considered complete.

        Returns:
            bool: Always True once gathering is complete.
        """
        ...
    def comma_and_list(self, **kwargs: Any) -> Any:
        """
        Return the list items as a comma-separated string with "and" before the last.

        Returns:
            str: Human-readable enumeration such as "Alice, Bob, and Carol".
        """
        ...
    def __contains__(self, item: Any) -> Any: ...
    def __iter__(self) -> Any: ...
    def _target_or_actual(self) -> Any: ...
    def __len__(self) -> Any: ...
    def __delitem__(self, index: Any) -> Any: ...
    def __reversed__(self) -> Any: ...
    def _fill_up_to(self, index: Any) -> Any: ...
    def __setitem__(self, index: Any, the_value: Any) -> Any: ...
    def __getitem__(self, index: Any) -> Any: ...
    def raise_undefined_index_error(self, index: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def __repr__(self) -> Any: ...
    def union(self, other_set: Any) -> Any:
        """
        Return the union of this list (as a set) and another collection.

        Args:
            other_set: Any iterable or DASet to union with.

        Returns:
            DASet: Elements from either this list or ``other_set``.
        """
        ...
    def intersection(self, other_set: Any) -> Any:
        """
        Return elements present in both this list (as a set) and another collection.

        Args:
            other_set: Any iterable or DASet to intersect with.

        Returns:
            DASet: Elements that appear in both this list and ``other_set``.
        """
        ...
    def difference(self, other_set: Any) -> Any:
        """
        Return elements in this list (as a set) that are not in another collection.

        Args:
            other_set: Any iterable or DASet to subtract.

        Returns:
            DASet: Elements present in this list but not in ``other_set``.
        """
        ...
    def isdisjoint(self, other_set: Any) -> Any:
        """
        Return True if this list and another collection share no elements.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if there is no overlap; False otherwise.
        """
        ...
    def issubset(self, other_set: Any) -> Any:
        """
        Return True if every element of this list is also in another collection.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if this list is a subset of ``other_set``; False
                otherwise.
        """
        ...
    def issuperset(self, other_set: Any) -> Any:
        """
        Return True if every element of another collection is in this list.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if ``other_set`` is a subset of this list; False
                otherwise.
        """
        ...
    def pronoun_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive pronoun phrase for the list followed by the target.

        Delegates to the single element when the list has exactly one item.
        For multiple elements returns "their <target>" (third person), "our
        <target>" (first person), or "your <target>" (second person).

        Args:
            target (str): The possessed noun phrase (e.g., ``"fish"``).
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: Possessive phrase such as "their fish" or "her fish".
        """
        ...
    def pronoun(self, **kwargs: Any) -> Any:
        """
        Return an objective pronoun appropriate for the list.

        Returns "them" for multiple elements, or delegates to the single
        element for a one-item list.

        Args:
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: A pronoun such as "them", "her", "him", "you", or "us".
        """
        ...
    def pronoun_objective(self, **kwargs: Any) -> Any:
        """Same as pronoun()."""
        ...
    def pronoun_subjective(self, **kwargs: Any) -> Any:
        """
        Return a subjective pronoun appropriate for the collection.

        Returns "they" for multiple elements, or delegates to the single
        element for a one-item collection.

        Args:
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: A pronoun such as "they", "she", "he", "you", or "we".
        """
        ...
    def _reorder(self, *pargs: Any) -> Any: ...
    def _reorder_buttons(self, classes: Any, index: Any) -> Any: ...
    def _edit_button(self, url: Any, classes: Any) -> Any: ...
    def _delete_button(self, url: Any, classes: Any) -> Any: ...
    def item_actions(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return HTML action buttons for editing and deleting a list item.

        Args:
            *pargs: First positional argument is the item object; second is
                its index. Additional positional arguments are attribute
                paths to follow up on when editing.
            **kwargs: Accepts ``edit`` (bool), ``delete`` (bool),
                ``reorder`` (bool), ``confirm`` (bool),
                ``ensure_complete`` (bool), ``read_only_attribute`` (str),
                ``edit_url_only`` (bool), and ``delete_url_only`` (bool).

        Returns:
            str: HTML string containing edit and/or delete buttons.
        """
        ...
    def _add_action_button(self, url: Any, classes: Any, icon: Any, the_message: Any) -> Any: ...
    def add_action(
        self,
        label: Any = ...,
        message: Any = ...,
        url_only: Any = ...,
        icon: Any = ...,
        color: Any = ...,
        size: Any = ...,
        block: Any = ...,
        classname: Any = ...,
    ) -> Any:
        """
        Return HTML for a button that adds a new item to the list.

        Args:
            label (str, optional): Button label text. Defaults to "Add an item"
                or "Add another" depending on whether items already exist.
            message (str, optional): Deprecated alias for ``label``.
            url_only (bool): If True, return only the action URL instead of
                the full button HTML. Defaults to False.
            icon (str): Font Awesome icon class name. Defaults to
                ``'plus-circle'``.
            color (str, optional): Bootstrap color name. Defaults to the
                configured ``'add'`` button color.
            size (str): Button size: ``'sm'``, ``'md'``, or ``'lg'``.
                Defaults to ``'sm'``.
            block (bool, optional): If True, add ``btn-block`` class.
            classname (str, optional): Extra CSS class(es) to add.

        Returns:
            str: HTML anchor element or URL string.
        """
        ...
    def hook_on_gather(self, *pargs: Any, **kwargs: Any) -> Any:
        """Override this method to run code just before the list is marked as gathered."""
        ...
    def hook_after_gather(self, *pargs: Any, **kwargs: Any) -> Any:
        """Override this method to run code just after the list is marked as gathered."""
        ...
    def hook_on_item_complete(self, item: Any, *pargs: Any, **kwargs: Any) -> Any:
        """
        Override this method to run code when an item becomes complete.

        Args:
            item: The item that has just been marked complete.
        """
        ...
    def hook_on_remove(self, item: Any, *pargs: Any, **kwargs: Any) -> Any:
        """
        Override this method to run code when an item is removed from the list.

        Args:
            item: The item being removed.
        """
        ...
    def __eq__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...

class DADict(DAObject):
    """
    A dictionary that docassemble can populate through interview questions.

    DADict behaves like a Python dictionary, but docassemble can ask questions
    to define entries. The gathering process is analogous to DAList, using
    ``there_are_any`` and ``there_is_another`` to determine when the dictionary
    is complete.

    Attributes:
        elements (dict): The underlying Python dictionary of items.
        gathered (bool): True when all entries have been gathered.
        auto_gather (bool): If True (the default), gathering is triggered
            automatically.
        object_type: A DAObject subclass (or ``.using()`` result) used when
            creating new values via ``initializeObject()``. Defaults to None.
        complete_attribute (str or None): An attribute that must be defined on
            each value before it is considered complete.
        there_are_any (bool): Whether any entries exist.
        there_is_another (bool): Whether there is another entry to add.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def set_object_type(self, object_type: Any) -> Any:
        """
        Set the object type used when creating new dictionary values.

        Args:
            object_type: A class or ``.using()`` result to use when
                ``initializeObject()`` creates new values.
        """
        ...
    def _trigger_gather(self) -> Any:
        """Triggers the gathering process."""
        ...
    def fix_instance_name(self, old_instance_name: Any, new_instance_name: Any) -> Any:
        """Substitutes a different instance name for the object and its subobjects."""
        ...
    def _set_instance_name_recursively(self, thename: Any, matching: Any = ...) -> Any:
        """Sets the instanceName attribute, if it is not already set, and that of subobjects."""
        ...
    def _mark_as_gathered_recursively(self) -> Any: ...
    def _reset_gathered_recursively(self) -> Any: ...
    def item_name(self, item: Any) -> Any:
        """
        Return the variable name for a dictionary entry by its key.

        Args:
            item: The key of the entry.

        Returns:
            str: Variable name such as ``'mydict["foo"]'``, suitable for use
                in ``force_ask()`` and similar functions.
        """
        ...
    def delitem(self, *pargs: Any) -> Any:
        """
        Delete entries by key.

        Args:
            *pargs: Keys of entries to delete. Keys not in the dictionary
                are silently ignored.
        """
        ...
    def invalidate_item(self, *pargs: Any) -> Any:
        """
        Invalidate one or more entries so they are re-evaluated.

        Args:
            *pargs: Keys of entries to invalidate.
        """
        ...
    def getitem_fresh(self, item: Any) -> Any:
        """
        Recompute and return the value for the given key, bypassing the cache.

        Args:
            item: The dictionary key to recompute.

        Returns:
            object: The freshly computed value for ``item``.
        """
        ...
    def all_false(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return True if all (or all specified) values are falsy.

        Args:
            *pargs: Optional keys or iterables of keys to check. If omitted,
                all keys are checked.
            **kwargs: Accepts ``exclusive`` (bool). When True, returns True
                only if the specified keys are the only falsy values.

        Returns:
            bool: True if all values for the specified (or all) keys are
                falsy; False otherwise.
        """
        ...
    def any_true(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return True if at least one (or one specified) value is truthy.

        Args:
            *pargs: Optional keys or iterables of keys to check.
            **kwargs: Passed through to ``all_false()``.

        Returns:
            bool: True if any value is truthy; False otherwise.
        """
        ...
    def any_false(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return True if at least one (or one specified) value is falsy.

        Args:
            *pargs: Optional keys or iterables of keys to check.
            **kwargs: Passed through to ``all_true()``.

        Returns:
            bool: True if any value is falsy; False otherwise.
        """
        ...
    def all_true(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return True if all (or all specified) values are truthy.

        Args:
            *pargs: Optional keys or iterables of keys to check. If omitted,
                all keys are checked.
            **kwargs: Accepts ``exclusive`` (bool). When True, returns True
                only if the specified keys are the only truthy values.

        Returns:
            bool: True if all values for the specified (or all) keys are
                truthy; False otherwise.
        """
        ...
    def true_values(self, insertion_order: Any = ...) -> Any:
        """
        Return a DAList of keys whose values are truthy.

        Args:
            insertion_order (bool): If True, preserve insertion order instead
                of sorting. Defaults to False.

        Returns:
            DAList: Keys whose associated values are truthy.
        """
        ...
    def false_values(self, insertion_order: Any = ...) -> Any:
        """
        Return a DAList of keys whose values are falsy.

        Args:
            insertion_order (bool): If True, preserve insertion order instead
                of sorting. Defaults to False.

        Returns:
            DAList: Keys whose associated values are falsy.
        """
        ...
    def _sorted_items(self) -> Any: ...
    def _sorted_elements_items(self) -> Any: ...
    def _sorted_iteritems(self) -> Any: ...
    def _sorted_elements_iteritems(self) -> Any: ...
    def initializeObject(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Create a new object and store it at the given key in the dictionary.

        Args:
            *pargs: First positional argument is the dictionary key to set.
                An optional second positional argument is the class (or
                ``.using()`` result) for the new object. Falls back to
                ``object_type``, then ``new_object_type`` (when
                ``ask_object_type`` is True), then ``DAObject``.
            **kwargs: Additional keyword arguments passed to the new object's
                constructor.

        Returns:
            DAObject: The newly created object stored at ``self[entry]``.
        """
        ...
    def new(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Initialize new dictionary entries as DAObject instances.

        For each key provided, creates an object of ``object_type`` (or
        ``DAObject`` if not set) and stores it under that key if the key does
        not already exist. Iterables in ``pargs`` are flattened automatically.

        Args:
            *pargs: Keys (or iterables of keys) for which to create new
                objects.
            **kwargs: Keyword arguments passed to each new object's
                constructor.
        """
        ...
    def reset_gathered(self, recursive: Any = ..., only_if_empty: Any = ..., mark_incomplete: Any = ...) -> Any:
        """
        Reset the gathered state so the collection will be re-gathered.

        Args:
            recursive (bool): If True, also reset gathering on nested DAList
                and DADict objects within the collection. Defaults to False.
            only_if_empty (bool): If True, only reset if the collection is
                empty. Defaults to False.
            mark_incomplete (bool): If True, delete the ``complete_attribute``
                on each item so items are treated as incomplete. Defaults to
                False.
        """
        ...
    def slice(self, *pargs: Any) -> Any:
        """
        Return a shallow copy of the dictionary restricted to the given keys.

        Args:
            *pargs: Keys to include in the result. A single callable argument
                is treated as a filter function ``f(value) -> bool``.

        Returns:
            DADict: A new DADict with ``gathered=True`` containing only the
                specified keys and their values.
        """
        ...
    def has_been_gathered(self) -> Any:
        """
        Return True if the gathering process for this dictionary has completed.

        Returns:
            bool: True if the dictionary has been gathered; False otherwise.
        """
        ...
    def itself(self, **kwargs: Any) -> Any:
        """
        Returns "themselves" unless the dictionary has only one element,
        in which case the method is called on the first element.
        """
        ...
    def do_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Given a verb like "eat," returns "do x eat" if there is
        more than one element. x is the string representation of the
        dictionary. If there is only one element, the method is called on
        the first element of the dictionary.
        """
        ...
    def did_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Given a verb like "eat," returns "did x eat" if there is
        more than one element. x is the string representation of the
        dictionary. If there is only one element, the method is called on
        the first element of the dictionary.
        """
        ...
    def were_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Given a target like "married", returns "were x married" if
        there is more than one element in the dictionary. x is the
        string representation of the dictionary. If there is only one
        element, the method is called on the first element.
        """
        ...
    def have_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Given a target like "married", returns "have x married" if
        there is more than one element in the dictionary. x is the
        string representation of the dictionary. If there is only one
        element, the method is called on the first element.
        """
        ...
    def does_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated present-tense form of a verb for the dictionary.

        Args:
            the_verb (str): The base form of the verb (e.g., ``"finish"``).
            **kwargs: Accepts ``person`` (str), ``language`` (str), ``past``
                (bool), and ``present`` (bool) for tense control.

        Returns:
            str: Conjugated verb, e.g. "finishes" for one player or "finish"
                for multiple players.
        """
        ...
    def did_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated past-tense form of a verb for the collection.

        Args:
            the_verb (str): The base form of the verb (e.g., ``"sue"``).
            **kwargs: Accepts ``person`` (str) and ``language`` (str).

        Returns:
            str: Past-tense conjugated verb, e.g. "sued".
        """
        ...
    def as_singular_noun(self) -> Any:
        """
        Return the singular noun form derived from the dictionary's instance name.

        E.g., ``player.as_singular_noun()`` returns ``"player"`` regardless
        of how many players are in the dictionary.

        Returns:
            str: Singular noun form of the trailing part of the instance name.
        """
        ...
    def quantity_noun(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a noun phrase combining the number of entries with the noun.

        Args:
            *pargs: Passed to the ``quantity_noun()`` function after the count.
            **kwargs: Passed through to ``quantity_noun()``.

        Returns:
            str: Phrase such as "3 players".
        """
        ...
    def as_noun(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a singular or plural noun form for the dictionary, derived from the instance name.

        E.g., ``player.as_noun()`` returns ``"player"`` or ``"players"``
        depending on how many entries are in the dictionary.

        Args:
            *pargs: If provided, the first argument overrides the noun instead
                of using the instance name.
            **kwargs: Accepts ``plural`` (bool), ``singular`` (bool),
                ``article`` (bool), ``some`` (bool), ``this`` (bool),
                ``capitalize`` (bool), and ``language`` (str).

        Returns:
            str: Noun form with optional article.
        """
        ...
    def possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive phrase using the dictionary's noun form and the target.

        Args:
            target (str): The possessed noun phrase (e.g., ``"fish"``).
            **kwargs: Passed to ``possessify()``; may include ``language``.

        Returns:
            str: E.g., "player's score" (one entry) or "players' scores"
                (multiple entries).
        """
        ...
    def number(self) -> Any:
        """
        Return the number of entries in the dictionary, triggering gathering if needed.

        Returns:
            int: Count of keys in the dictionary.
        """
        ...
    def gathering_started(self) -> Any:
        """
        Return True if any items have been gathered or ``there_are_any`` has been set.

        Returns:
            bool: True if gathering has started; False otherwise.
        """
        ...
    def number_gathered(self, if_started: Any = ...) -> Any:
        """Returns the number of elements in the dictionary that have been gathered so far."""
        ...
    def number_as_word(self, language: Any = ...) -> Any:
        """
        Returns the number of keys in the dictionary, spelling out the number if ten
        or below.  Forces the gathering of the dictionary items if necessary.
        """
        ...
    def complete_elements(self, complete_attribute: Any = ...) -> Any:
        """Returns a dictionary containing the key/value pairs that are complete."""
        ...
    def _sorted_keys(self) -> Any: ...
    def _sorted_elements_keys(self) -> Any: ...
    def _complete_attributes(self, complete_attribute: Any = ...) -> Any: ...
    def _validate(self, item_object_type: Any, complete_attribute: Any, keys: Any = ...) -> Any: ...
    def cancel_add_or_edit(self) -> Any: ...
    def gathered_and_complete(self) -> Any:
        """
        Ensure every value in the dictionary is complete and return True.

        Returns:
            bool: Always True once all values are complete.
        """
        ...
    def gather(
        self,
        item_object_type: Any = ...,
        number: Any = ...,
        minimum: Any = ...,
        complete_attribute: Any = ...,
        keys: Any = ...,
    ) -> Any:
        """
        Trigger the gathering process for the dictionary and return True.

        Args:
            item_object_type: Class to use when creating values; overrides
                ``object_type``.
            number (int, optional): Collect exactly this many entries.
            minimum (int, optional): Minimum number of entries to collect.
            complete_attribute (str or list, optional): Attribute(s) that
                must be defined for a value to be considered complete.
            keys (list, optional): Specific keys to validate.

        Returns:
            bool: Always True once gathering is complete.
        """
        ...
    def _sorted_elements_values(self) -> Any: ...
    def _sorted_values(self) -> Any: ...
    def _new_item_init_callback(self) -> Any: ...
    def comma_and_list(self, **kwargs: Any) -> Any:
        """
        Return the dictionary keys as a comma-separated string with "and" before the last.

        Returns:
            str: Human-readable enumeration of keys such as "alpha, beta, and gamma".
        """
        ...
    def __getitem__(self, index: Any) -> Any: ...
    def raise_undefined_index_error(self, index: Any) -> Any: ...
    def __setitem__(self, key: Any, the_value: Any) -> Any: ...
    def __contains__(self, item: Any) -> Any: ...
    def keys(self) -> Any:
        """
        Return the keys of the dictionary as a sorted list, triggering gathering.

        Returns:
            list: Sorted list of keys.
        """
        ...
    def values(self) -> Any:
        """
        Return the values of the dictionary, triggering gathering.

        Returns:
            dict_values: The underlying dictionary's values view.
        """
        ...
    def update(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Update the dictionary with the keys and values of another mapping.

        Args:
            *pargs: An optional first positional argument is a dict or DADict
                whose entries are merged in.
            **kwargs: Additional key/value pairs to merge.
        """
        ...
    def pop(self, *pargs: Any) -> Any:
        """
        Remove a key and return its value.

        Args:
            *pargs: First argument is the key to remove; an optional second
                argument is the default value when the key is absent.

        Returns:
            object: The value associated with the removed key.
        """
        ...
    def popitem(self) -> Any:
        """
        Remove and return an arbitrary (key, value) pair.

        Returns:
            tuple: A ``(key, value)`` pair removed from the dictionary.
        """
        ...
    def setdefault(self, *pargs: Any) -> Any:
        """
        Return the value for a key, inserting a default if the key is absent.

        Args:
            *pargs: First argument is the key; optional second argument is
                the default value (defaults to None).

        Returns:
            object: The existing or newly set value for the key.
        """
        ...
    def get(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return the value for a key, or a default if the key is absent.

        Args:
            *pargs: First argument is the key; optional second argument is
                the default (defaults to None).

        Returns:
            object: Value for the key, or the default.
        """
        ...
    def clear(self) -> Any:
        """Removes all the items from the dictionary."""
        ...
    def copy(self) -> Any:
        """Returns a copy of the dictionary."""
        ...
    def has_key(self, key: Any) -> Any:
        """
        Return True if the key exists in the dictionary.

        Args:
            key: The key to test.

        Returns:
            bool: True if ``key`` is present; False otherwise.
        """
        ...
    def item(self, key: Any) -> Any:
        """
        Return the value for a key, or a blank DAEmpty if the key does not exist.

        Args:
            key: The dictionary key to look up.

        Returns:
            object: The value for ``key``, or a ``DAEmpty`` instance.
        """
        ...
    def items(self) -> Any:
        """
        Return the items of the dictionary, triggering gathering.

        Returns:
            dict_items: Key/value pairs view of the underlying dictionary.
        """
        ...
    def iteritems(self) -> Any:
        """Iterates through the keys and values of the dictionary."""
        ...
    def iterkeys(self) -> Any:
        """Iterates through the keys of the dictionary."""
        ...
    def itervalues(self) -> Any:
        """Iterates through the values of the dictionary."""
        ...
    def __iter__(self) -> Any: ...
    def _target_or_actual(self) -> Any: ...
    def __len__(self) -> Any: ...
    def __reversed__(self) -> Any: ...
    def __delitem__(self, key: Any) -> Any: ...
    def __missing__(self, key: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def __repr__(self) -> Any: ...
    def union(self, other_set: Any) -> Any:
        """
        Return the union of this dictionary's values (as a set) and another collection.

        Args:
            other_set: Any iterable or DASet to union with.

        Returns:
            DASet: Values from either this dictionary or ``other_set``.
        """
        ...
    def intersection(self, other_set: Any) -> Any:
        """
        Return values present in both this dictionary and another collection.

        Args:
            other_set: Any iterable or DASet to intersect with.

        Returns:
            DASet: Values that appear in both this dictionary and ``other_set``.
        """
        ...
    def difference(self, other_set: Any) -> Any:
        """
        Return values in this dictionary that are not in another collection.

        Args:
            other_set: Any iterable or DASet to subtract.

        Returns:
            DASet: Values in this dictionary but not in ``other_set``.
        """
        ...
    def isdisjoint(self, other_set: Any) -> Any:
        """
        Return True if this dictionary's values and another collection share no elements.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if there is no overlap; False otherwise.
        """
        ...
    def issubset(self, other_set: Any) -> Any:
        """
        Return True if every value in this dictionary is also in another collection.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if this dictionary's values are a subset of ``other_set``.
        """
        ...
    def issuperset(self, other_set: Any) -> Any:
        """
        Return True if every element of another collection is in this dictionary's values.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if ``other_set`` is a subset of this dictionary's
                values; False otherwise.
        """
        ...
    def pronoun_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive pronoun phrase for the collection followed by the target.

        Args:
            target (str): The possessed noun phrase (e.g., ``"fish"``).
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: Possessive phrase such as "their fish".
        """
        ...
    def pronoun(self, **kwargs: Any) -> Any:
        """
        Return an objective pronoun appropriate for the dictionary.

        Returns "them" for multiple values, or delegates to the single
        value for a one-item dictionary.

        Args:
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: A pronoun such as "them", "her", "him", "you", or "us".
        """
        ...
    def pronoun_objective(self, **kwargs: Any) -> Any:
        """Same as pronoun()."""
        ...
    def pronoun_subjective(self, **kwargs: Any) -> Any:
        """
        Return a subjective pronoun appropriate for the collection.

        Returns "they" for multiple elements, or delegates to the single
        element for a one-item collection.

        Args:
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: A pronoun such as "they", "she", "he", "you", or "we".
        """
        ...
    def _edit_button(self, url: Any, classes: Any) -> Any: ...
    def _delete_button(self, url: Any, classes: Any) -> Any: ...
    def item_actions(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return HTML action buttons for editing and deleting a dictionary entry.

        Args:
            *pargs: First positional argument is the value object; second is
                its key. Additional positional arguments are attribute paths
                to follow up on when editing.
            **kwargs: Accepts ``edit`` (bool), ``delete`` (bool),
                ``confirm`` (bool), ``ensure_complete`` (bool),
                ``read_only_attribute`` (str), ``edit_url_only`` (bool),
                and ``delete_url_only`` (bool).

        Returns:
            str: HTML string containing edit and/or delete buttons.
        """
        ...
    def _add_action_button(self, url: Any, classes: Any, icon: Any, the_message: Any) -> Any: ...
    def add_action(
        self,
        label: Any = ...,
        message: Any = ...,
        url_only: Any = ...,
        icon: Any = ...,
        color: Any = ...,
        size: Any = ...,
        block: Any = ...,
        classname: Any = ...,
    ) -> Any:
        """Returns HTML for adding an item to a dict"""
        ...
    def _new_elements(self) -> Any: ...
    def hook_on_gather(self, *pargs: Any, **kwargs: Any) -> Any:
        """Override this method to run code just before the dictionary is marked as gathered."""
        ...
    def hook_after_gather(self, *pargs: Any, **kwargs: Any) -> Any:
        """Override this method to run code just after the dictionary is marked as gathered."""
        ...
    def hook_on_item_complete(self, item: Any, *pargs: Any, **kwargs: Any) -> Any:
        """
        Override this method to run code when an item becomes complete.

        Args:
            item: The item that has just been marked complete.
        """
        ...
    def hook_on_remove(self, item: Any, *pargs: Any, **kwargs: Any) -> Any:
        """
        Override this method to run code when an entry is removed from the dictionary.

        Args:
            item: The value being removed.
        """
        ...
    def __eq__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...

class DAOrderedDict(DADict):
    """
    A DADict that preserves insertion order (backed by OrderedDict).

    Inherits all methods from DADict. Keys and items are iterated in
    insertion order rather than sorted order.
    """
    def _new_elements(self) -> Any: ...
    def _sorted_items(self) -> Any: ...
    def _sorted_elements_items(self) -> Any: ...
    def _sorted_iteritems(self) -> Any: ...
    def _sorted_elements_iteritems(self) -> Any: ...
    def _sorted_keys(self) -> Any: ...
    def _sorted_elements_keys(self) -> Any: ...
    def _sorted_values(self) -> Any: ...
    def _sorted_elements_values(self) -> Any: ...

class DASet(DAObject):
    """
    A set that docassemble can populate through interview questions.

    DASet behaves like a Python set, but docassemble can ask questions to
    add members. Gathering is controlled by the same ``there_are_any`` /
    ``there_is_another`` attributes as DAList.

    Attributes:
        elements (set): The underlying Python set of items.
        gathered (bool): True when all items have been gathered.
        auto_gather (bool): If True (the default), gathering is triggered
            automatically.
        there_are_any (bool): Whether any items exist.
        there_is_another (bool): Whether there is another item to add.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def gathered_and_complete(self) -> Any:
        """
        Ensure every item in the set is complete and return True.

        Returns:
            bool: Always True once all items are complete.
        """
        ...
    def complete_elements(self, complete_attribute: Any = ...) -> Any:
        """
        Return a gathered DASet of only the complete items.

        Args:
            complete_attribute (str or list, optional): Override the set's
                own ``complete_attribute`` setting.

        Returns:
            DASet: A new DASet with ``gathered=True`` containing only
                complete items.
        """
        ...
    def filter(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a new DASet containing only items matching the given attribute values.

        Args:
            *pargs: Optional first argument sets the instance name of the
                returned set; defaults to this set's instance name.
            **kwargs: Attribute name/value pairs used to filter items.

        Returns:
            DASet: A gathered copy containing only matching items.
        """
        ...
    def _trigger_gather(self) -> Any:
        """Triggers the gathering process."""
        ...
    def reset_gathered(self, recursive: Any = ..., only_if_empty: Any = ..., mark_incomplete: Any = ...) -> Any:
        """
        Reset the gathered state so the collection will be re-gathered.

        Args:
            recursive (bool): If True, also reset gathering on nested DAList
                and DADict objects within the collection. Defaults to False.
            only_if_empty (bool): If True, only reset if the collection is
                empty. Defaults to False.
            mark_incomplete (bool): If True, delete the ``complete_attribute``
                on each item so items are treated as incomplete. Defaults to
                False.
        """
        ...
    def has_been_gathered(self) -> Any:
        """
        Return True if the gathering process for this set has completed.

        Returns:
            bool: True if the set has been gathered; False otherwise.
        """
        ...
    def _reset_gathered_recursively(self) -> Any: ...
    def copy(self) -> Any:
        """Returns a copy of the set."""
        ...
    def clear(self) -> Any:
        """Removes all the items from the set."""
        ...
    def remove(self, elem: Any) -> Any:
        """
        Remove an element from the set.

        Args:
            elem: The element to remove.

        Raises:
            KeyError: If ``elem`` is not present in the set.
        """
        ...
    def discard(self, elem: Any) -> Any:
        """
        Remove an element from the set if it is present; do nothing otherwise.

        Args:
            elem: The element to discard.
        """
        ...
    def pop(self) -> Any:
        """
        Remove and return an arbitrary element from the set.

        Returns:
            object: An arbitrary element removed from the set.

        Raises:
            KeyError: If the set is empty.
        """
        ...
    def add(self, *pargs: Any) -> Any:
        """
        Add items to the set, unpacking iterables automatically.

        Args:
            *pargs: Items to add. If an argument is a DAList, DASet, or other
                iterable (but not a string), its members are added individually.
        """
        ...
    def is_user(self) -> Any:
        """Returns True if the set has one element and the one element is the user, otherwise False."""
        ...
    def itself(self, **kwargs: Any) -> Any:
        """
        Returns "themselves" unless the set has only one element,
        in which case the method is called on the first element.
        """
        ...
    def do_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Given a verb like "eat," returns "do x eat" if there is
        more than one element. x is the string representation of the
        set. If there is only one element, the method is called on
        the first element of the set.
        """
        ...
    def did_question(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Given a verb like "eat," returns "did x eat" if there is
        more than one element. x is the string representation of the
        set. If there is only one element, the method is called on
        the first element of the set.
        """
        ...
    def were_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Given a target like "married", returns "were x married" if
        there is more than one element in the set. x is the string
        representation of the set. If there is only one element, the
        method is called on the first element.
        """
        ...
    def have_question(self, the_target: Any, **kwargs: Any) -> Any:
        """
        Given a target like "married", returns "have x married" if
        there is more than one element in the set. x is the string
        representation of the set. If there is only one element, the
        method is called on the first element.
        """
        ...
    def does_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated present-tense form of a verb for the set.

        Args:
            the_verb (str): The base form of the verb (e.g., ``"finish"``).
            **kwargs: Accepts ``person`` (str), ``language`` (str), ``past``
                (bool), and ``present`` (bool) for tense control.

        Returns:
            str: Conjugated verb, e.g. "finishes" for one item or "finish"
                for multiple items.
        """
        ...
    def did_verb(self, the_verb: Any, **kwargs: Any) -> Any:
        """
        Return the correctly conjugated past-tense form of a verb for the collection.

        Args:
            the_verb (str): The base form of the verb (e.g., ``"sue"``).
            **kwargs: Accepts ``person`` (str) and ``language`` (str).

        Returns:
            str: Past-tense conjugated verb, e.g. "sued".
        """
        ...
    def as_singular_noun(self) -> Any:
        """
        Return the singular noun form derived from the set's instance name.

        E.g., ``player.as_singular_noun()`` returns ``"player"`` regardless
        of how many players are in the set.

        Returns:
            str: Singular noun form of the trailing part of the instance name.
        """
        ...
    def quantity_noun(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a noun phrase combining the number of items with the noun.

        Args:
            *pargs: Passed to the ``quantity_noun()`` function after the count.
            **kwargs: Passed through to ``quantity_noun()``.

        Returns:
            str: Phrase such as "3 players".
        """
        ...
    def as_noun(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Return a singular or plural noun form for the set, derived from the instance name.

        E.g., ``player.as_noun()`` returns ``"player"`` or ``"players"``
        depending on how many items are in the set.

        Args:
            *pargs: If provided, the first argument overrides the noun instead
                of using the instance name.
            **kwargs: Accepts ``plural`` (bool), ``singular`` (bool),
                ``article`` (bool), ``some`` (bool), ``this`` (bool),
                ``capitalize`` (bool), and ``language`` (str).

        Returns:
            str: Noun form with optional article.
        """
        ...
    def number(self) -> Any:
        """
        Return the number of items in the set, triggering gathering if needed.

        Returns:
            int: Count of items in the set.
        """
        ...
    def gathering_started(self) -> Any:
        """
        Return True if any items have been gathered or ``there_are_any`` has been set.

        Returns:
            bool: True if gathering has started; False otherwise.
        """
        ...
    def number_gathered(self, if_started: Any = ...) -> Any:
        """
        Return the count of items gathered so far, without triggering gathering.

        Args:
            if_started (bool): If True, trigger gathering when gathering has
                not yet started. Defaults to False.

        Returns:
            int: Number of items currently in the set.
        """
        ...
    def number_as_word(self, language: Any = ...) -> Any:
        """
        Return the number of items spelled out as a word when ten or fewer.

        Args:
            language (str, optional): Language code for localization.

        Returns:
            str: Spelled-out number (e.g., "three") for counts up to ten;
                numeral string otherwise.
        """
        ...
    def gather(self, number: Any = ..., minimum: Any = ...) -> Any:
        """
        Trigger the gathering process for the set and return True.

        Args:
            number (int, optional): Collect exactly this many items.
            minimum (int, optional): Minimum number of items to collect.

        Returns:
            bool: Always True once gathering is complete.
        """
        ...
    def comma_and_list(self, **kwargs: Any) -> Any:
        """
        Return the set items as a comma-separated string with "and" before the last.

        Returns:
            str: Human-readable enumeration of items such as "Alice, Bob, and Carol".
        """
        ...
    def __contains__(self, item: Any) -> Any: ...
    def __iter__(self) -> Any: ...
    def _target_or_actual(self) -> Any: ...
    def __len__(self) -> Any: ...
    def __reversed__(self) -> Any: ...
    def __and__(self, operand: Any) -> Any: ...
    def __or__(self, operand: Any) -> Any: ...
    def __iand__(self, operand: Any) -> Any: ...
    def __ior__(self, operand: Any) -> Any: ...
    def __isub__(self, operand: Any) -> Any: ...
    def __ixor__(self, operand: Any) -> Any: ...
    def __rand__(self, operand: Any) -> Any: ...
    def __ror__(self, operand: Any) -> Any: ...
    def __hash__(self) -> Any: ...
    def __add__(self, other: Any) -> Any: ...
    def __sub__(self, other: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def __repr__(self) -> Any: ...
    def union(self, other_set: Any) -> Any:
        """
        Return a new set that is the union of this set and another collection.

        Args:
            other_set: Any iterable or DASet to union with.

        Returns:
            DASet: Elements from either this set or ``other_set``.
        """
        ...
    def intersection(self, other_set: Any) -> Any:
        """
        Return a new set of elements present in both this set and another collection.

        Args:
            other_set: Any iterable or DASet to intersect with.

        Returns:
            DASet: Elements that appear in both this set and ``other_set``.
        """
        ...
    def difference(self, other_set: Any) -> Any:
        """
        Return a new set of elements in this set that are not in another collection.

        Args:
            other_set: Any iterable or DASet to subtract.

        Returns:
            DASet: Elements in this set but not in ``other_set``.
        """
        ...
    def isdisjoint(self, other_set: Any) -> Any:
        """
        Return True if this set and another collection share no elements.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if there is no overlap; False otherwise.
        """
        ...
    def issubset(self, other_set: Any) -> Any:
        """
        Return True if every element of this set is also in another collection.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if this set is a subset of ``other_set``; False
                otherwise.
        """
        ...
    def issuperset(self, other_set: Any) -> Any:
        """
        Return True if every element of another collection is in this set.

        Args:
            other_set: Any iterable or DASet to compare against.

        Returns:
            bool: True if ``other_set`` is a subset of this set; False
                otherwise.
        """
        ...
    def pronoun_possessive(self, target: Any, **kwargs: Any) -> Any:
        """
        Return a possessive pronoun phrase for the collection followed by the target.

        Args:
            target (str): The possessed noun phrase (e.g., ``"fish"``).
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: Possessive phrase such as "their fish".
        """
        ...
    def pronoun(self, **kwargs: Any) -> Any:
        """
        Return an objective pronoun appropriate for the set.

        Returns "them" for multiple items, or delegates to the single
        item for a one-item set.

        Args:
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: A pronoun such as "them", "her", "him", "you", or "us".
        """
        ...
    def pronoun_objective(self, **kwargs: Any) -> Any:
        """Same as pronoun()."""
        ...
    def pronoun_subjective(self, **kwargs: Any) -> Any:
        """
        Return a subjective pronoun appropriate for the collection.

        Returns "they" for multiple elements, or delegates to the single
        element for a one-item collection.

        Args:
            **kwargs: Accepts ``person`` (str) and ``capitalize`` (bool).

        Returns:
            str: A pronoun such as "they", "she", "he", "you", or "we".
        """
        ...
    def hook_on_gather(self, *pargs: Any, **kwargs: Any) -> Any:
        """Override this method to run code just before the set is marked as gathered."""
        ...
    def hook_after_gather(self, *pargs: Any, **kwargs: Any) -> Any:
        """Override this method to run code just after the set is marked as gathered."""
        ...
    def hook_on_item_complete(self, item: Any, *pargs: Any, **kwargs: Any) -> Any:
        """
        Override this method to run code when an item becomes complete.

        Args:
            item: The item that has just been marked complete.
        """
        ...
    def hook_on_remove(self, item: Any, *pargs: Any, **kwargs: Any) -> Any:
        """
        Override this method to run code when an item is removed from the set.

        Args:
            item: The item being removed.
        """
        ...
    def __eq__(self, other: Any) -> Any: ...

class DAFile(DAObject):
    """
    Represent an uploaded, generated, or stored file in a docassemble interview.

    DAFile objects track a file by a server-side number and offer methods to
    read, write, convert, and display the file.

    Attributes:
        number (int): Internal file number used to locate the file on the
            server.
        ok (bool): True when the file has been initialized with a valid
            number.
        filename (str): Original or assigned filename, including extension.
        extension (str): Lowercase file extension (e.g., ``'pdf'``, ``'docx'``).
        mimetype (str): MIME type of the file.
        initialized (bool): True after the file storage slot has been created.
        alt_text (str): Alternative text for image display.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def convert_to(self, output_extension: Any, output_to: Any = ...) -> Any:
        """
        Convert this file to a different format.

        Args:
            output_extension (str): Target file extension (e.g., ``'pdf'``).
            output_to (DAFile or DAFileList, optional): Destination file
                object. Defaults to converting this file in-place.

        Raises:
            DAError: If the file type cannot be identified or the conversion
                is not supported.
        """
        ...
    def fix_up(self) -> Any:
        """
        Attempt to repair the file in-place if it is corrupt or malformed.

        Raises:
            Exception: If the file is corrupt and cannot be repaired.
        """
        ...
    def set_alt_text(self, alt_text: Any) -> Any:
        """
        Set the alternative text for the file (used in image display).

        Args:
            alt_text (str): The alt text to associate with this file.
        """
        ...
    def get_alt_text(self) -> Any:
        """
        Return the alternative text for the file, or None if not set.

        Returns:
            str or None: The alt text string, or None if not defined.
        """
        ...
    def set_mimetype(self, mimetype: Any) -> Any:
        """
        Set the MIME type of the file and update the extension accordingly.

        Args:
            mimetype (str): MIME type string (e.g., ``'image/jpeg'``).
        """
        ...
    def __str__(self) -> Any: ...
    def initialize(self, **kwargs: Any) -> Any:
        """
        Create the file on the server if it does not already exist and prepare it for use.

        Args:
            **kwargs: Accepts ``filename`` (str), ``mimetype`` (str),
                ``extension`` (str), ``content`` (str), ``markdown`` (str),
                ``alt_text`` (str), ``number`` (int), and
                ``reinitialize`` (bool). Pass ``reinitialize=True`` to delete
                the existing file and create a fresh one.
        """
        ...
    def retrieve(self) -> Any:
        """
        Ensure the file is available locally and update ``file_info``.

        Raises:
            DAError: If the file cannot be retrieved.
        """
        ...
    def size_in_bytes(self) -> Any:
        """
        Return the size of the file in bytes.

        Returns:
            int: Number of bytes in the file.
        """
        ...
    def slurp(self, auto_decode: Any = ...) -> Any:
        """
        Return the entire contents of the file as a string or bytes.

        Args:
            auto_decode (bool): If True (the default), return a ``str`` for
                text and JSON files; otherwise return ``bytes``.

        Returns:
            str or bytes: File contents.

        Raises:
            DAError: If the file does not yet exist on disk.
        """
        ...
    def readlines(self) -> Any:
        """
        Return the lines of the file as a list of strings.

        Returns:
            list[str]: Lines of the file including newline characters.

        Raises:
            DAError: If the file does not yet exist on disk.
        """
        ...
    def write(self, content: Any, binary: Any = ...) -> Any:
        """
        Write content to the file, replacing any existing contents.

        Args:
            content (str or bytes): The content to write.
            binary (bool): If True, open the file in binary mode for writing
                bytes. Defaults to False.
        """
        ...
    def copy_into(self, other_file: Any) -> Any:
        """
        Replace this file's contents with the contents of another file.

        Args:
            other_file (DAFile, DAFileList, DAFileCollection, DAStaticFile,
                or str): Source file object or filesystem path.
        """
        ...
    def extract_pages(self, first: Any = ..., last: Any = ..., output_to: Any = ...) -> Any: ...
    def bates_number(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Apply Bates numbering to this file or a set of provided files.

        Args:
            *pargs: Optional source files (DAFile, DAFileList, DAFileCollection,
                or DAStaticFile) to Bates-number. If none provided, this file
                is used.
            **kwargs: Accepts ``filename`` (str), ``prefix`` (str, default
                ``'TEST'``), ``digits`` (int, default 5), ``start`` (int,
                default 1), ``area`` (str, one of ``'TOP_LEFT'``,
                ``'TOP_RIGHT'``, ``'BOTTOM_RIGHT'``, ``'BOTTOM_LEFT'``),
                ``font_size`` (int, default 10),
                ``offset_horizontal`` (int), ``offset_vertical`` (int).

        Raises:
            DAError: If Bates numbering fails.
        """
        ...
    def make_ocr_pdf(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Replace this file's contents with an OCR'd PDF of this or other files.

        Args:
            *pargs: Optional source files to OCR. Defaults to this file.
            **kwargs: Accepts ``language`` (str), ``psm`` (int), and
                ``preserve_color`` (bool).
        """
        ...
    def make_ocr_pdf_in_background(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Asynchronously replace this file's contents with an OCR'd PDF.

        Starts a background Celery task. The result is a chord handle.

        Args:
            *pargs: Optional source files to OCR. Defaults to this file.
            **kwargs: Accepts ``language`` (str), ``psm`` (int),
                ``preserve_color`` (bool), ``dafilelist`` (DAFileList), and
                ``filename`` (str).

        Returns:
            AsyncResult: A Celery chord handle for the background task.
        """
        ...
    def _is_pdf(self) -> Any: ...
    def get_docx_variables(self) -> Any:
        """
        Return a list of Jinja2 variable names used in a DOCX template file.

        Returns:
            list[str]: Variable names referenced in the document template.
        """
        ...
    def get_pdf_fields(self) -> Any:
        """
        Return a list of form fields found in the PDF document.

        Returns:
            list[tuple]: Each tuple contains field information: name, value,
                position, page number, field type, and flags.
        """
        ...
    def from_url(self, url: Any) -> Any:
        """
        Download content from a URL and store it as this file's contents.

        Args:
            url (str): The URL to download.
        """
        ...
    def uses_acroform(self) -> Any:
        """
        Return True if the PDF file uses AcroForm fields.

        Returns:
            bool: True if the file uses AcroForm; False otherwise.
        """
        ...
    def is_encrypted(self) -> Any:
        """
        Return True if the file is an encrypted PDF.

        Returns:
            bool: True if the file is an encrypted PDF; False otherwise.
        """
        ...
    def _make_pdf_thumbnail(self, page: Any, both_formats: Any = ...) -> Any:
        """Creates a page image for the first page of a PDF file."""
        ...
    def pngs_ready(self) -> Any:
        """
        Return True if the PNG page images for the PDF have been generated.

        Returns:
            bool: True if all PNG images are ready; False otherwise.
        """
        ...
    def _delete_pngs(self) -> Any: ...
    def _make_pngs_for_pdf(self) -> Any: ...
    def num_pages(self) -> Any:
        """
        Return the number of pages in the file.

        Returns:
            int: Number of pages for a PDF; 1 for all other file types.

        Raises:
            DAError: If the file has no file number assigned.
        """
        ...
    def _pdf_page_path(self, page: Any) -> Any: ...
    def _path_ready(self, the_path: Any) -> Any: ...
    def page_path(self, page: Any, prefix: Any, wait: Any = ...) -> Any:
        """
        Return the filesystem path for a PDF page image.

        Args:
            page (int): One-based page number.
            prefix (str): Image type prefix, either ``'page'`` or ``'screen'``.
            wait (bool): If True, wait for the image to be generated if not
                yet ready. Defaults to True.

        Returns:
            str or None: Filesystem path to the PNG image, or None if not
                ready and ``wait`` is False.

        Raises:
            DAError: If the file has no number or page count information.
        """
        ...
    def cloud_path(self, filename: Any = ...) -> Any:
        """
        Return the cloud storage path for the file, or None if cloud storage is not enabled.

        Args:
            filename (str, optional): Specific filename within the file's
                cloud storage directory.

        Returns:
            str or None: Cloud storage path (S3 or Azure Blob), or None.

        Raises:
            DAError: If the file has no file number assigned.
        """
        ...
    def path(self) -> Any:
        """
        Return the filesystem path at which the file can be accessed.

        Returns:
            str: Absolute filesystem path to the file.

        Raises:
            DAError: If the file has no file number assigned or the path
                cannot be determined.
        """
        ...
    def commit(self) -> Any:
        """Persist any changes to the file so they are available in the future."""
        ...
    def show(self, width: Any = ..., wait: Any = ..., alt_text: Any = ...) -> Any:
        """
        Return markup that displays the file inline.

        Args:
            width (str or int, optional): Display width for images.
            wait (bool): If True, wait for PDF page images to be generated
                before returning markup. Defaults to True.
            alt_text (str, optional): Alternative text for the image.

        Returns:
            str: Markup string for embedding the file in interview output.
        """
        ...
    def _pdf_pages(self, width: Any) -> Any: ...
    def url_for(self, **kwargs: Any) -> Any:
        """
        Return a URL at which the file can be accessed.

        Args:
            **kwargs: Accepts ``temporary`` (bool), ``external`` (bool), and
                ``attachment`` (bool).

        Returns:
            str: URL string for the file.
        """
        ...
    def set_attributes(self, **kwargs: Any) -> Any:
        """
        Set server-side attributes for the file.

        Args:
            **kwargs: Accepts ``private`` (bool), ``persistent`` (bool), and
                ``filename`` (str).
        """
        ...
    def user_access(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Grant or revoke access to the file for specific users.

        Args:
            *pargs: User objects whose access should be modified.
            **kwargs: Accepts ``allow`` (bool, default True) and ``access``
                (str) to specify access level.
        """
        ...
    def privilege_access(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Grant or revoke access to the file for users with specific privileges.

        Args:
            *pargs (str): Privilege names to grant access.
            **kwargs: Accepts ``disallow`` (str, list, or ``'all'``) to
                revoke access from named privileges or all privileges.
        """
        ...

class DAFileCollection(DAObject):
    """
    Represent a collection of DAFile objects for the same document in multiple formats.

    Created by the ``attachments`` feature to group a document's PDF, DOCX,
    and RTF renderings. Each format is accessible as an attribute (e.g.,
    ``collection.pdf``, ``collection.docx``).

    Attributes:
        pdf (DAFile): The PDF version of the document, if available.
        docx (DAFile): The DOCX version of the document, if available.
        rtf (DAFile): The RTF version of the document, if available.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _extension_list(self) -> Any: ...
    def fix_up(self) -> Any:
        """
        Attempt to repair each file in the collection in-place.

        Raises:
            Exception: If a file is corrupt and cannot be repaired.
        """
        ...
    def set_alt_text(self, alt_text: Any) -> Any:
        """
        Set the alternative text on each file in the collection.

        Args:
            alt_text (str): The alt text to set on all files.
        """
        ...
    def get_alt_text(self) -> Any:
        """
        Return the alternative text of the first file in the collection, or None.

        Returns:
            str or None: Alt text of the first file, or None if not defined.
        """
        ...
    def uses_acroform(self) -> Any:
        """
        Return True if the collection has a PDF file that uses AcroForm.

        Returns:
            bool: True if the PDF uses AcroForm; False otherwise.
        """
        ...
    def is_encrypted(self) -> Any:
        """
        Return True if the collection has an encrypted PDF file.

        Returns:
            bool: True if the PDF is encrypted; False otherwise.
        """
        ...
    def num_pages(self) -> Any:
        """
        Return the page count of the PDF file in the collection, or 1 if none.

        Returns:
            int: Number of pages in the PDF, or 1 if no PDF is present.
        """
        ...
    def _first_file(self) -> Any: ...
    def path(self) -> Any:
        """
        Return the filesystem path of the first available file in the collection.

        Returns:
            str or None: Absolute path to the first available file, or None.
        """
        ...
    def get_docx_variables(self) -> Any:
        """
        Return a list of Jinja2 variable names used in a DOCX template file.

        Returns:
            list[str]: Variable names referenced in the document template.
        """
        ...
    def get_pdf_fields(self) -> Any:
        """
        Return a list of form fields found in the PDF document.

        Returns:
            list[tuple]: Each tuple contains field information: name, value,
                position, page number, field type, and flags.
        """
        ...
    def url_for(self, **kwargs: Any) -> Any:
        """
        Return a URL to the first available file in the collection.

        Args:
            **kwargs: Passed through to the individual file's ``url_for()``.

        Returns:
            str: URL for the first available format.

        Raises:
            DAError: If no file is found in the collection.
        """
        ...
    def set_attributes(self, **kwargs: Any) -> Any:
        """
        Set server-side attributes on each file in the collection.

        Args:
            **kwargs: Accepts ``private`` (bool) and ``persistent`` (bool).
                The ``filename`` argument is ignored.
        """
        ...
    def user_access(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Grant or revoke access to all files in the collection for specific users.

        Args:
            *pargs: User objects whose access should be modified.
            **kwargs: Passed through to each file's ``user_access()``.
        """
        ...
    def privilege_access(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Grant or revoke access to all files in the collection for specific privileges.

        Args:
            *pargs (str): Privilege names to grant access.
            **kwargs: Passed through to each file's ``privilege_access()``.
        """
        ...
    def show(self, **kwargs: Any) -> Any:
        """
        Return markup that displays each file in the collection inline.

        Returns:
            str: Markup for embedding the collection files in interview output.
        """
        ...
    def extract_pages(self, first: Any = ..., last: Any = ...) -> Any:
        """
        Extract a page range from the PDF and return a new DAFile.

        Args:
            first (int, optional): First page to include (1-based). Defaults
                to 1.
            last (int, optional): Last page to include (inclusive). Defaults
                to the last page.

        Returns:
            DAFile: A new DAFile containing the extracted pages.

        Raises:
            DAError: If no PDF is available.
        """
        ...
    def bates_number(self, **kwargs: Any) -> Any:
        """
        Apply Bates numbering to the collection's PDF file in-place.

        Args:
            **kwargs: Passed through to the PDF file's ``bates_number()``.

        Raises:
            DAError: If the collection has no PDF attribute.
        """
        ...
    def make_ocr_pdf(self, **kwargs: Any) -> Any:
        """
        Replace the collection's PDF file with an OCR'd version.

        Args:
            **kwargs: Passed through to the PDF file's ``make_ocr_pdf()``.

        Raises:
            DAError: If the collection has no PDF attribute.
        """
        ...
    def make_ocr_pdf_in_background(self, **kwargs: Any) -> Any:
        """
        Asynchronously replace the collection's PDF with an OCR'd version.

        Args:
            **kwargs: Passed through to the PDF file's
                ``make_ocr_pdf_in_background()``.

        Returns:
            AsyncResult: A Celery chord handle for the background task.

        Raises:
            DAError: If the collection has no PDF attribute.
        """
        ...
    def __str__(self) -> Any: ...

class DAFileList(DAList):
    """
    A list of DAFile objects, typically from a multi-file upload field.

    Inherits from DAList and is used internally to manage uploaded files.
    Each element is a DAFile. Most file operations (e.g., ``path()``,
    ``url_for()``, ``show()``) delegate to the first element.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def fix_up(self) -> Any:
        """
        Attempt to repair each file in the list in-place.

        Raises:
            Exception: If a file is corrupt and cannot be repaired.
        """
        ...
    def set_alt_text(self, alt_text: Any) -> Any:
        """
        Set the alternative text on each file in the list.

        Args:
            alt_text (str): The alt text to assign to all files.
        """
        ...
    def get_alt_text(self) -> Any:
        """
        Return the alternative text of the first file in the list, or None.

        Returns:
            str or None: Alt text of the first file, or None if the list is
                empty or no alt text is defined.
        """
        ...
    def num_pages(self) -> Any:
        """
        Return the total page count across all files in the list.

        Returns:
            int: Sum of pages for PDF files; non-PDF files count as one page
                each.
        """
        ...
    def uses_acroform(self) -> Any:
        """
        Return True if the first file is a PDF that uses AcroForm.

        Returns:
            bool or None: True if the first file uses AcroForm; None if the
                list is empty.
        """
        ...
    def is_encrypted(self) -> Any:
        """
        Return True if the first file is an encrypted PDF.

        Returns:
            bool or None: True if the first file is an encrypted PDF; None
                if the list is empty.
        """
        ...
    def convert_to(self, output_extension: Any, output_to: Any = ...) -> Any:
        """
        Convert each file in the list to a different format.

        Args:
            output_extension (str): Target file extension (e.g., ``'pdf'``).
            output_to (DAFile or DAFileList, optional): Destination file;
                converts in-place when None.
        """
        ...
    def size_in_bytes(self) -> Any:
        """
        Return the size in bytes of the first file, or None if the list is empty.

        Returns:
            int or None: Byte count of the first file, or None.
        """
        ...
    def slurp(self, auto_decode: Any = ...) -> Any:
        """
        Return the contents of the first file, or None if the list is empty.

        Args:
            auto_decode (bool): If True (the default), return ``str`` for
                text files; otherwise return ``bytes``.

        Returns:
            str, bytes, or None: File contents, or None if the list is empty.
        """
        ...
    def show(self, width: Any = ..., alt_text: Any = ...) -> Any:
        """
        Return markup that displays each file in the list inline.

        Args:
            width (str or int, optional): Display width for images.
            alt_text (str, optional): Alternative text for images.

        Returns:
            str: Markup for embedding the files in interview output.
        """
        ...
    def path(self) -> Any:
        """
        Return the filesystem path of the first file in the list.

        Returns:
            str or None: Path to the first file, or None if the list is empty.
        """
        ...
    def get_docx_variables(self) -> Any:
        """
        Return a list of Jinja2 variable names used in a DOCX template file.

        Returns:
            list[str]: Variable names referenced in the document template.
        """
        ...
    def get_pdf_fields(self) -> Any:
        """
        Return a list of form fields found in the PDF document.

        Returns:
            list[tuple]: Each tuple contains field information: name, value,
                position, page number, field type, and flags.
        """
        ...
    def url_for(self, **kwargs: Any) -> Any:
        """
        Return a URL for the first file in the list.

        Args:
            **kwargs: Passed through to the first file's ``url_for()``.

        Returns:
            str or None: URL for the first file, or None if the list is empty.
        """
        ...
    def set_attributes(self, **kwargs: Any) -> Any:
        """
        Set server-side attributes on each file in the list.

        Args:
            **kwargs: Accepts ``private`` (bool) and ``persistent`` (bool).
                The ``filename`` argument is ignored.
        """
        ...
    def user_access(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Grant or revoke access to all files in the list for specific users.

        Args:
            *pargs: User objects whose access should be modified.
            **kwargs: Passed through to each file's ``user_access()``.
        """
        ...
    def privilege_access(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Grant or revoke access to all files in the list for specific privileges.

        Args:
            *pargs (str): Privilege names to grant access.
            **kwargs: Passed through to each file's ``privilege_access()``.
        """
        ...
    def extract_pages(self, first: Any = ..., last: Any = ...) -> Any:
        """
        Extract a page range from the PDF and return a new DAFile.

        Args:
            first (int, optional): First page to include (1-based). Defaults
                to 1.
            last (int, optional): Last page to include (inclusive). Defaults
                to the last page.

        Returns:
            DAFile: A new DAFile containing the extracted pages.

        Raises:
            DAError: If no PDF is available.
        """
        ...
    def bates_number(self, **kwargs: Any) -> Any:
        """
        Apply Bates numbering to the list of files and store the result in the first file.

        Args:
            **kwargs: Passed through to the first file's ``bates_number()``.
        """
        ...
    def make_ocr_pdf(self, **kwargs: Any) -> Any:
        """
        OCR the list of files and store the result in the first file.

        Args:
            **kwargs: Passed through to the first file's ``make_ocr_pdf()``.
        """
        ...
    def make_ocr_pdf_in_background(self, **kwargs: Any) -> Any:
        """
        Asynchronously OCR the list of files and store the result in the first file.

        Args:
            **kwargs: Passed through to the first file's
                ``make_ocr_pdf_in_background()``.

        Returns:
            AsyncResult or None: Celery chord handle, or None if the list is
                empty.
        """
        ...

class DAStaticFile(DAObject):
    """
    Represent a static file included with a docassemble package.

    Provides access to files in the ``data/static/`` directory of a package.
    Supports the same display and information methods as DAFile.

    Attributes:
        filename (str): The package-relative or fully qualified filename.
        package (str): The Python package that contains the file.
        extension (str): Lowercase file extension.
        mimetype (str): MIME type of the file.
        alt_text (str): Alternative text for image display.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _populate(self) -> Any: ...
    def get_alt_text(self) -> Any:
        """
        Return the alternative text for the file, or None if not set.

        Returns:
            str or None: The alt text string, or None if not defined.
        """
        ...
    def set_alt_text(self, alt_text: Any) -> Any:
        """
        Set the alternative text for the file (used in image display).

        Args:
            alt_text (str): The alt text to associate with this file.
        """
        ...
    def _get_unqualified_reference(self) -> Any: ...
    def show(self, width: Any = ..., alt_text: Any = ...) -> Any:
        """
        Return markup that displays the static file inline.

        Args:
            width (str or int, optional): Display width for images.
            alt_text (str, optional): Alternative text for the image.

        Returns:
            str: Markup string for embedding the file in interview output.
        """
        ...
    def _pdf_pages(self, width: Any) -> Any: ...
    def uses_acroform(self) -> Any:
        """
        Return True if the static file is a PDF that uses AcroForm.

        Returns:
            bool: True if the file uses AcroForm; False otherwise.
        """
        ...
    def is_encrypted(self) -> Any:
        """
        Return True if the file is an encrypted PDF.

        Returns:
            bool: True if the file is an encrypted PDF; False otherwise.
        """
        ...
    def size_in_bytes(self) -> Any:
        """
        Return the size of the file in bytes.

        Returns:
            int: Number of bytes in the file.
        """
        ...
    def slurp(self, auto_decode: Any = ...) -> Any:
        """
        Return the entire contents of the file as a string or bytes.

        Args:
            auto_decode (bool): If True (the default), return a ``str`` for
                text and JSON files; otherwise return ``bytes``.

        Returns:
            str or bytes: File contents.

        Raises:
            DAError: If the file does not yet exist on disk.
        """
        ...
    def path(self) -> Any:
        """
        Return the filesystem path at which the static file can be accessed.

        Returns:
            str or None: Absolute filesystem path to the file, or None if not
                found.
        """
        ...
    def get_docx_variables(self) -> Any:
        """
        Return a list of Jinja2 variable names used in a DOCX template file.

        Returns:
            list[str]: Variable names referenced in the document template.
        """
        ...
    def get_pdf_fields(self) -> Any:
        """
        Return a list of form fields found in the PDF document.

        Returns:
            list[tuple]: Each tuple contains field information: name, value,
                position, page number, field type, and flags.
        """
        ...
    def url_for(self, **kwargs: Any) -> Any:
        """
        Return a URL that points to the static file.

        Args:
            **kwargs: Optional keyword arguments. ``external=True`` generates
                an absolute URL; ``attachment=True`` sets the
                Content-Disposition header to trigger a download.

        Returns:
            str: URL to the static file.
        """
        ...
    def _is_pdf(self) -> Any: ...
    def __str__(self) -> Any: ...

class DAEmail(DAObject):
    """
    An email message received through docassemble's email-receiving feature.

    Attributes:
        subject (str): Subject line of the received email.
        from_address (DAEmailRecipient): Sender of the email.
        to_address (DAEmailRecipientList): Primary recipients.
        cc_address (DAEmailRecipientList): Carbon-copy recipients.
        reply_to (DAEmailRecipient): Reply-to address, if present.
        body_text (str): Plain-text body of the email.
        body_html (str): HTML body of the email.
        attachments (DAFileList): Files attached to the email.
    """
    def __str__(self) -> Any: ...

class DAEmailRecipient(DAObject):
    """
    A single email recipient with a name and address.

    Attributes:
        name (str): Display name of the recipient.
        address (str): Email address of the recipient.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def email_address(self, include_name: Any = ...) -> Any:
        """
        Return the recipient's email address, optionally including the display name.

        Args:
            include_name (bool or None): If True, include the name in RFC 5321
                format (``"Name" <address>``). If None (the default), include
                the name only when it is non-empty.

        Returns:
            str: Formatted email address string.
        """
        ...
    def exists(self) -> Any: ...
    def __str__(self) -> Any: ...

class DAEmailRecipientList(DAList):
    """A list of DAEmailRecipient objects used to address an outgoing email."""
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...

class DATemplate(DAObject):
    """
    A Markdown template created from a ``template`` block.

    Attributes:
        subject (str): Subject line of the template (used for email subjects).
        content (str): Markdown body of the template.
        decorations (list): List of decoration identifiers attached to the
            template.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def show(self, **kwargs: Any) -> Any:
        """
        Return the rendered content of the template as a string.

        Returns:
            str: Rendered template content.
        """
        ...
    def show_as_markdown(self, **kwargs: Any) -> Any:
        """
        Return the raw Markdown content of the template.

        Returns:
            str: Markdown source of the template content.
        """
        ...
    def __str__(self) -> Any: ...

class DAEmpty:
    """
    An object that silently absorbs any attribute access or operation.

    DAEmpty avoids triggering errors about missing information by returning
    another DAEmpty for any attribute access, returning empty values for
    string conversion and length, and absorbing arithmetic operations.

    Attributes:
        str (str): The string value returned when the object is converted to
            text. Defaults to the empty string.
    """
    def __init__(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __getattr__(self, thename: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def __dir__(self) -> Any: ...
    def __contains__(self, item: Any) -> Any: ...
    def __iter__(self) -> Any: ...
    def __len__(self) -> Any: ...
    def __reversed__(self) -> Any: ...
    def __getitem__(self, index: Any) -> Any: ...
    def __setitem__(self, index: Any, val: Any) -> Any: ...
    def __delitem__(self, index: Any) -> Any: ...
    def __call__(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __repr__(self) -> Any: ...
    def __add__(self, other: Any) -> Any: ...
    def __sub__(self, other: Any) -> Any: ...
    def __mul__(self, other: Any) -> Any: ...
    def __floordiv__(self, other: Any) -> Any: ...
    def __mod__(self, other: Any) -> Any: ...
    def __divmod__(self, other: Any) -> Any: ...
    def __pow__(self, other: Any) -> Any: ...
    def __lshift__(self, other: Any) -> Any: ...
    def __rshift__(self, other: Any) -> Any: ...
    def __and__(self, other: Any) -> Any: ...
    def __xor__(self, other: Any) -> Any: ...
    def __or__(self, other: Any) -> Any: ...
    def __div__(self, other: Any) -> Any: ...
    def __truediv__(self, other: Any) -> Any: ...
    def __radd__(self, other: Any) -> Any: ...
    def __rsub__(self, other: Any) -> Any: ...
    def __rmul__(self, other: Any) -> Any: ...
    def __rdiv__(self, other: Any) -> Any: ...
    def __rtruediv__(self, other: Any) -> Any: ...
    def __rfloordiv__(self, other: Any) -> Any: ...
    def __rmod__(self, other: Any) -> Any: ...
    def __rdivmod__(self, other: Any) -> Any: ...
    def __rpow__(self, other: Any) -> Any: ...
    def __rlshift__(self, other: Any) -> Any: ...
    def __rrshift__(self, other: Any) -> Any: ...
    def __rand__(self, other: Any) -> Any: ...
    def __ror__(self, other: Any) -> Any: ...
    def __neg__(self) -> Any: ...
    def __pos__(self) -> Any: ...
    def __abs__(self) -> Any: ...
    def __invert__(self) -> Any: ...
    def __complex__(self) -> Any: ...
    def __int__(self) -> Any: ...
    def __float__(self) -> Any: ...
    def __oct__(self) -> Any: ...
    def __hex__(self) -> Any: ...
    def __index__(self) -> Any: ...
    def __le__(self, other: Any) -> Any: ...
    def __ge__(self, other: Any) -> Any: ...
    def __gt__(self, other: Any) -> Any: ...
    def __lt__(self, other: Any) -> Any: ...
    def __eq__(self, other: Any) -> Any: ...
    def __ne__(self, other: Any) -> Any: ...
    def __hash__(self) -> Any: ...
    def as_dict(self) -> Any: ...
    def to_json(self) -> Any: ...

class DALink(DAObject):
    """
    A hyperlink to a URL that renders appropriately in each output context.

    Attributes:
        url (str): The destination URL.
        anchor_text (str): The visible link text.
    """
    def __str__(self) -> Any: ...
    def show(self) -> Any:
        """
        Return a hyperlink rendered for the current output context.

        Returns:
            str or docx Run: A DOCX hyperlink object when evaluated inside a
                DOCX template; a Markdown hyperlink string otherwise.
        """
        ...

def last_access_time(
    include_privileges: Any = ..., exclude_privileges: Any = ..., include_cron: Any = ..., timezone: Any = ...
) -> Any:
    """
    Return the most recent time the interview was accessed.

    Args:
        include_privileges (list[str] or str or None): If provided, only
            consider accesses by users with one of these privilege names.
        exclude_privileges (list[str] or str or None): If provided, ignore
            accesses by users with one of these privilege names.
        include_cron (bool): If True, include accesses by cron jobs.
            Defaults to False.
        timezone (str or None): IANA timezone for the returned datetime.
            Defaults to the interview's default timezone.

    Returns:
        DADateTime or None: The most recent access time, or None if no
            matching access record exists.
    """
    ...

def last_access_delta(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return the time elapsed since the interview was last accessed.

    Accepts the same arguments as :func:`last_access_time`.

    Returns:
        datetime.timedelta: Elapsed time since last access, or a zero
            timedelta if there is no access record.
    """
    ...

def last_access_days(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return the number of days since the interview was last accessed.

    Accepts the same arguments as :func:`last_access_time`.

    Returns:
        float: Days since last access.
    """
    ...

def last_access_hours(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return the number of hours since the interview was last accessed.

    Accepts the same arguments as :func:`last_access_time`.

    Returns:
        float: Hours since last access.
    """
    ...

def last_access_minutes(*pargs: Any, **kwargs: Any) -> Any:
    """
    Return the number of minutes since the interview was last accessed.

    Accepts the same arguments as :func:`last_access_time`.

    Returns:
        float: Minutes since last access.
    """
    ...

def returning_user(minutes: Any = ..., hours: Any = ..., days: Any = ...) -> Any:
    """
    Return True if the user is returning after a period of inactivity.

    Args:
        minutes (float or None): Return True if more than this many minutes
            have elapsed since the last access.
        hours (float or None): Return True if more than this many hours have
            elapsed.
        days (float or None): Return True if more than this many days have
            elapsed.

    Returns:
        bool: True if the user is returning after the specified period (or
            after 6 hours by default); False otherwise or on POST requests.
    """
    ...

def action_arguments(*args: Any, **kwargs: Any) -> Any: ...
def action_argument(*args: Any, **kwargs: Any) -> Any: ...
def timezone_list() -> Any:
    """
    Return a sorted list of all available IANA timezone names.

    Returns:
        list[str]: Sorted list of timezone strings (e.g. ``'America/New_York'``).
    """
    ...

def as_datetime(the_date: Any, timezone: Any = ...) -> Any:
    """
    Convert a date or date string to a timezone-aware DADateTime object.

    Args:
        the_date (datetime.date, datetime.datetime, or str): Date or
            date/time value to convert. String values are parsed with
            ``dateutil``.
        timezone (str or None): IANA timezone name to attach. If the value
            already carries timezone information it is converted to this
            zone; otherwise the timezone is applied as-is. Defaults to
            the interview's default timezone.

    Returns:
        DADateTime: Timezone-aware datetime.
    """
    ...

def current_datetime(timezone: Any = ...) -> Any:
    """
    Return the current date and time as a DADateTime object.

    Args:
        timezone (str or None): IANA timezone name. If None, the interview's
            default timezone is used.

    Returns:
        DADateTime: Current date and time in the specified timezone.
    """
    ...

def date_difference(starting: Any = ..., ending: Any = ..., timezone: Any = ...) -> Any:
    """
    Return the difference between two dates.

    Args:
        starting (datetime.date, datetime.datetime, str, or None): Start of
            the interval. Defaults to the current datetime.
        ending (datetime.date, datetime.datetime, str, or None): End of the
            interval. Defaults to the current datetime.
        timezone (str or None): IANA timezone name used when localizing
            naive datetimes. Defaults to the interview's default timezone.

    Returns:
        DateTimeDelta: Object with ``weeks``, ``days``, ``hours``,
            ``minutes``, ``seconds``, ``years``, and ``delta`` attributes
            expressing the difference, and ``start``/``end`` attributes
            holding the resolved datetime objects.
    """
    ...

def date_interval(**kwargs: Any) -> Any:
    """
    Return a relative date/time interval.

    All keyword arguments are forwarded to
    ``dateutil.relativedelta.relativedelta``. Common arguments include
    ``years``, ``months``, ``weeks``, ``days``, ``hours``, ``minutes``,
    and ``seconds``.

    Returns:
        dateutil.relativedelta.relativedelta: Interval that can be added to
            or subtracted from a ``DADateTime`` or ``datetime`` object.
    """
    ...

def year_of(the_date: Any, language: Any = ...) -> Any:
    """
    Return the year component of a date.

    Args:
        the_date (datetime.date, datetime.datetime, or str): The date to
            extract the year from.
        language (str or None): Unused; retained for API consistency.

    Returns:
        int: Four-digit year.
    """
    ...

def month_of(the_date: Any, as_word: Any = ..., language: Any = ...) -> Any:
    """
    Return the month component of a date.

    Args:
        the_date (datetime.date, datetime.datetime, or str): The date to
            extract the month from.
        as_word (bool): If True, return the full month name (e.g.
            ``'January'``); otherwise return the month as an integer.
        language (str or None): Language code for localizing the month name.
            Defaults to the current interview language.

    Returns:
        int or str: Month number (1–12) or localized month name.
    """
    ...

def day_of(the_date: Any, language: Any = ...) -> Any:
    """
    Return the day-of-month component of a date.

    Args:
        the_date (datetime.date, datetime.datetime, or str): The date to
            extract the day from.
        language (str or None): Unused; retained for API consistency.

    Returns:
        int: Day of the month (1–31).
    """
    ...

def dow_of(the_date: Any, as_word: Any = ..., language: Any = ...) -> Any:
    """
    Return the day of the week for a date.

    Args:
        the_date (datetime.date, datetime.datetime, or str): The date to
            inspect.
        as_word (bool): If True, return the full weekday name (e.g.
            ``'Monday'``); otherwise return an integer from 1 (Monday) to
            7 (Sunday) per ISO 8601.
        language (str or None): Language code for localizing the weekday
            name. Defaults to the current interview language.

    Returns:
        int or str: Day-of-week number or localized weekday name.
    """
    ...

def format_date(the_date: Any, format: Any = ..., language: Any = ...) -> Any:
    """
    Return a date formatted as a localized string.

    Args:
        the_date (datetime.date, datetime.datetime, or str): Date to format.
        format (str or None): Babel date-format pattern (e.g. ``'long'``,
            ``'short'``, ``'MM/dd/yyyy'``). Defaults to the interview's
            configured date format or ``'long'``.
        language (str or None): Language/locale code. Defaults to the current
            interview language.

    Returns:
        str: Formatted date string, or ``''`` for an empty date.
    """
    ...

def format_datetime(the_date: Any, format: Any = ..., language: Any = ...) -> Any:
    """
    Return a date and time formatted as a localized string.

    Args:
        the_date (datetime.datetime or str): Date/time to format.
        format (str or None): Babel datetime-format pattern. Defaults to the
            interview's configured datetime format or ``'long'``.
        language (str or None): Language/locale code. Defaults to the current
            interview language.

    Returns:
        str: Formatted datetime string, or ``''`` for an empty date.
    """
    ...

def format_time(the_time: Any, format: Any = ..., language: Any = ...) -> Any:
    """
    Return a time formatted as a localized string.

    Args:
        the_time (datetime.time, datetime.datetime, or str): Time to format.
        format (str or None): Babel time-format pattern. Defaults to the
            interview's configured time format or ``'short'``.
        language (str or None): Language/locale code. Defaults to the current
            interview language.

    Returns:
        str: Formatted time string, or ``''`` for an empty time.
    """
    ...

def today(timezone: Any = ..., format: Any = ...) -> Any:
    """
    Return today's date at midnight as a DADateTime object.

    Args:
        timezone (str or None): IANA timezone name. If None, the interview's
            default timezone is used.
        format (str or None): If provided, return the date formatted as a
            string using this Babel date-format pattern instead of a
            DADateTime.

    Returns:
        DADateTime or str: Midnight today in the given timezone, or a
            formatted date string if ``format`` is specified.
    """
    ...

def get_default_timezone(*args: Any, **kwargs: Any) -> Any: ...
def user_logged_in(*args: Any, **kwargs: Any) -> Any: ...
def interface(*args: Any, **kwargs: Any) -> Any: ...
def user_privileges(*args: Any, **kwargs: Any) -> Any: ...
def user_has_privilege(*args: Any, **kwargs: Any) -> Any: ...
def user_info(*args: Any, **kwargs: Any) -> Any: ...
def current_context(*args: Any, **kwargs: Any) -> Any: ...
def task_performed(task: Any, persistent: Any = ...) -> Any:
    """
    Return True if the given task has been performed at least once.

    Args:
        task (str): Task name to check.
        persistent (bool or str): If True or a scope string, check the
            persistent task store instead of the session. Defaults to False.

    Returns:
        bool: True if the task counter is greater than zero; False otherwise.
    """
    ...

def task_not_yet_performed(task: Any, persistent: Any = ...) -> Any:
    """
    Return True if the given task has never been performed.

    Args:
        task (str): Task name to check.
        persistent (bool or str): If True or a scope string, check the
            persistent task store. Defaults to False.

    Returns:
        bool: True if the task has not been performed; False otherwise.
    """
    ...

def mark_task_as_performed(task: Any, persistent: Any = ...) -> Any:
    """
    Increment the task counter by 1.

    Args:
        task (str): Task name to mark.
        persistent (bool or str): If True or a scope string, update the
            persistent task store. Defaults to False.

    Returns:
        int: Updated task counter value.
    """
    ...

def times_task_performed(task: Any, persistent: Any = ...) -> Any:
    """
    Return the number of times the task has been performed.

    Args:
        task (str): Task name to query.
        persistent (bool or str): If True or a scope string, query the
            persistent task store. Defaults to False.

    Returns:
        int: Number of times the task has been performed (0 if never).
    """
    ...

def set_task_counter(task: Any, times: Any, persistent: Any = ...) -> Any:
    """
    Set the task counter to a specific value.

    Args:
        task (str): Task name to update.
        times (int): Value to set the counter to.
        persistent (bool or str): If True or a scope string, update the
            persistent task store. Defaults to False.
    """
    ...

def background_action(*args: Any, **kwargs: Any) -> Any: ...
def background_response(*args: Any, **kwargs: Any) -> Any: ...
def background_response_action(*args: Any, **kwargs: Any) -> Any: ...
def background_error_action(*args: Any, **kwargs: Any) -> Any: ...

us: Any

class DARedis(DAObject):
    """
    An interface for reading and writing data in the Redis cache.

    Provides convenience wrappers for pickling Python objects to Redis and
    exposes the raw ``redis-py`` client via attribute access.
    """
    def key(self, keyname: Any) -> Any:
        """
        Return a namespaced Redis key prefixed with the current interview name.

        Args:
            keyname (str): Suffix to append to the interview-based prefix.

        Returns:
            str: Fully qualified Redis key.
        """
        ...
    def get_data(self, key: Any) -> Any:
        """
        Retrieve and unpickle a Python object stored in Redis.

        Args:
            key (str): Redis key.

        Returns:
            object: Unpickled value, or None if the key does not exist or
                unpickling fails.
        """
        ...
    def set_data(self, key: Any, data: Any, expire: Any = ...) -> Any:
        """
        Pickle and store a Python object in Redis.

        Args:
            key (str): Redis key under which to store the value.
            data (object): Python object to pickle and store.
            expire (int or None): Optional TTL in seconds. If None, the key
                does not expire.

        Raises:
            DAError: If ``expire`` is provided but is not an integer.
        """
        ...
    def __getattr__(self, funcname: Any) -> Any: ...

class DACloudStorage(DAObject):
    """
    An interface for interacting with cloud object storage (S3 or Azure Blob Storage).

    Attributes:
        provider (str): Cloud provider identifier (used only for custom
            configurations).
        config (dict): Provider-specific configuration (used only for custom
            configurations).
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    @property
    def conn(self) -> Any:
        """The underlying cloud connection object (``boto3.resource('s3')`` or ``BlockBlobService``)."""
        ...
    @property
    def client(self) -> Any:
        """The ``boto3.client('s3')`` object for low-level S3 operations."""
        ...
    @property
    def bucket(self) -> Any:
        """The ``boto3 Bucket`` object for the configured S3 bucket."""
        ...
    @property
    def bucket_name(self) -> Any:
        """The name of the Amazon S3 bucket."""
        ...
    @property
    def container_name(self) -> Any:
        """The name of the Azure Blob Storage container."""
        ...

class DAGoogleAPI(DAObject):
    """
    A helper for accessing Google APIs using service-account credentials.

    Provides factory methods that return authenticated client objects for
    Google Drive, Sheets, Cloud Storage, and Cloud Vision.
    """
    def api_credentials(self, scope: Any) -> Any:
        """
        Return an OAuth2 credentials object for the given API scope.

        Args:
            scope (str): OAuth2 scope URL.

        Returns:
            google.oauth2.credentials.Credentials: Authenticated credentials.
        """
        ...
    def http(self, scope: Any) -> Any:
        """
        Return an authorized ``httplib2.Http`` object for the given API scope.

        Args:
            scope (str): OAuth2 scope URL.

        Returns:
            google_auth_httplib2.AuthorizedHttp: Authorized HTTP transport.
        """
        ...
    def drive_service(self) -> Any:
        """
        Return an authenticated Google Drive v3 service object.

        Returns:
            googleapiclient.discovery.Resource: Authorized Drive service.
        """
        ...
    def sheets_service(self) -> Any:
        """
        Return an authenticated Google Sheets v4 service object.

        Returns:
            googleapiclient.discovery.Resource: Authorized Sheets service.
        """
        ...
    def cloud_credentials(self, scopes: Any = ...) -> Any:
        """
        Return Google Cloud service-account credentials.

        Args:
            scopes (list[str] or None): OAuth2 scopes to request. If None,
                uses the default scopes configured on the service account.

        Returns:
            google.oauth2.service_account.Credentials: Service account
                credentials.
        """
        ...
    def project_id(self) -> Any:
        """
        Return the Google Cloud project ID from the service-account credentials.

        Returns:
            str: Google Cloud project ID.
        """
        ...
    def google_cloud_storage_client(self) -> Any:
        """
        Return an authenticated Google Cloud Storage client.

        Returns:
            google.cloud.storage.Client: Authorized Cloud Storage client.
        """
        ...
    def google_cloud_vision_client(self) -> Any:
        """
        Return an authenticated Google Cloud Vision client.

        Returns:
            google.cloud.vision.ImageAnnotatorClient: Authorized Vision client.
        """
        ...

MachineLearningEntry: Any

SimpleTextMachineLearner: Any

SVMMachineLearner: Any

RandomForestMachineLearner: Any

def set_live_help_status(*args: Any, **kwargs: Any) -> Any: ...
def chat_partners_available(*args: Any, **kwargs: Any) -> Any: ...
def phone_number_in_e164(*args: Any, **kwargs: Any) -> Any: ...
def phone_number_formatted(*args: Any, **kwargs: Any) -> Any: ...
def phone_number_is_valid(*args: Any, **kwargs: Any) -> Any: ...
def countries_list(*args: Any, **kwargs: Any) -> Any: ...
def country_name(*args: Any, **kwargs: Any) -> Any: ...
def write_record(*args: Any, **kwargs: Any) -> Any: ...
def read_records(*args: Any, **kwargs: Any) -> Any: ...
def delete_record(*args: Any, **kwargs: Any) -> Any: ...
def variables_as_json(*args: Any, **kwargs: Any) -> Any: ...
def all_variables(*args: Any, **kwargs: Any) -> Any: ...
def ocr_file(
    image_file: Any,
    language: Any = ...,
    psm: Any = ...,
    f: Any = ...,
    l: Any = ...,
    x: Any = ...,
    y: Any = ...,
    W: Any = ...,
    H: Any = ...,
    use_google: Any = ...,
    raw_result: Any = ...,
) -> Any:
    """
    Run optical character recognition on image or PDF files and return the text.

    Args:
        image_file (DAFile or DAFileList): File(s) to OCR.
        language (str or None): Tesseract language code (e.g. ``'eng'``).
            Defaults to the interview language.
        psm (int): Tesseract page segmentation mode. Defaults to 6.
        f (int or None): First page to OCR (PDF only).
        l (int or None): Last page to OCR (PDF only).
        x (int or None): Left edge of the crop rectangle in pixels.
        y (int or None): Top edge of the crop rectangle in pixels.
        W (int or None): Width of the crop rectangle in pixels.
        H (int or None): Height of the crop rectangle in pixels.
        use_google (bool): If True, use Google Cloud Vision instead of
            Tesseract.
        raw_result (bool): If True and ``use_google`` is True, return the
            raw Vision API JSON response.

    Returns:
        str: Recognized text, or a localized error message.

    Raises:
        DAError: If Tesseract or Google Cloud Vision fails.
    """
    ...

def ocr_file_in_background(*pargs: Any, **kwargs: Any) -> Any:
    """
    Start OCR on image or PDF files as a background Celery task.

    Args:
        *pargs: First positional argument is the file or list of files to OCR
            (DAFile or DAFileList). An optional second positional argument is a
            UI notification identifier.
        **kwargs: Optional keyword arguments including ``language``,
            ``psm``, ``f``, ``l``, ``x``, ``y``, ``W``, ``H``,
            ``use_google`` (bool), ``raw_result`` (bool), and ``message``.

    Returns:
        celery.result.AsyncResult: A Celery task result object. Call
            ``.get()`` to wait for the result.
    """
    ...

def read_qr(image_file: Any, f: Any = ..., l: Any = ..., x: Any = ..., y: Any = ..., W: Any = ..., H: Any = ...) -> Any:
    """
    Decode QR codes found in image or PDF files.

    Args:
        image_file (DAFile or DAFileList): File(s) to scan for QR codes.
        f (int or None): First page to scan (PDF only).
        l (int or None): Last page to scan (PDF only).
        x (int or None): Left edge of the crop rectangle in pixels.
        y (int or None): Top edge of the crop rectangle in pixels.
        W (int or None): Width of the crop rectangle in pixels.
        H (int or None): Height of the crop rectangle in pixels.

    Returns:
        list[str]: Decoded QR code data strings, in scan order.
    """
    ...

def get_sms_session(phone_number: Any, config: Any = ...) -> Any:
    """
    Return the SMS session information for a phone number.

    Args:
        phone_number (str): Phone number to look up.
        config (str): Twilio configuration name. Defaults to ``'default'``.

    Returns:
        dict or None: Session data dict (without internal keys), or None if no
            session exists for the number.
    """
    ...

def initiate_sms_session(
    phone_number: Any, yaml_filename: Any = ..., email: Any = ..., new: Any = ..., send: Any = ..., config: Any = ...
) -> Any:
    """
    Initiate an SMS session for a phone number.

    Args:
        phone_number (str): Recipient's phone number.
        yaml_filename (str or None): Interview YAML file to start. Defaults to
            the current interview.
        email (str or None): Email address to associate with the SMS user.
        new (bool): If True, always create a new session even if one exists.
        send (bool): If True (default), send an SMS invite immediately.
        config (str): Twilio configuration name. Defaults to ``'default'``.

    Returns:
        bool: True.
    """
    ...

def terminate_sms_session(phone_number: Any, config: Any = ...) -> Any:
    """
    Terminate the SMS session for a phone number.

    Args:
        phone_number (str): Phone number whose session should be ended.
        config (str): Twilio configuration name. Defaults to ``'default'``.

    Returns:
        bool: True if a session was terminated; False otherwise.
    """
    ...

def language_from_browser(*args: Any, **kwargs: Any) -> Any: ...
def device(*args: Any, **kwargs: Any) -> Any: ...
def interview_email(*args: Any, **kwargs: Any) -> Any: ...
def get_emails(*args: Any, **kwargs: Any) -> Any: ...
def plain(*args: Any, **kwargs: Any) -> Any: ...
def bold(*args: Any, **kwargs: Any) -> Any: ...
def italic(*args: Any, **kwargs: Any) -> Any: ...
def path_and_mimetype(file_ref: Any) -> Any:
    """
    Return the filesystem path and MIME type of a file.

    Args:
        file_ref (DAFile, DAFileList, DAFileCollection, DAStaticFile, or int):
            Reference to the file.

    Returns:
        tuple[str, str]: ``(path, mimetype)`` — absolute filesystem path and
            MIME type string.
    """
    ...

def states_list(*args: Any, **kwargs: Any) -> Any: ...
def state_name(*args: Any, **kwargs: Any) -> Any: ...
def subdivision_type(*args: Any, **kwargs: Any) -> Any: ...
def indent(*args: Any, **kwargs: Any) -> Any: ...
def raw(*args: Any, **kwargs: Any) -> Any: ...
def fix_punctuation(*args: Any, **kwargs: Any) -> Any: ...
def set_progress(*args: Any, **kwargs: Any) -> Any: ...
def get_progress(*args: Any, **kwargs: Any) -> Any: ...
def referring_url(*args: Any, **kwargs: Any) -> Any: ...
def run_python_module(module: Any, arguments: Any = ...) -> Any:
    """
    Run a Python module as a subprocess and return its output.

    Args:
        module (str): Dotted module name or a ``.py`` filename (resolved
            relative to the current package). A leading ``.`` is treated as
            a relative import.
        arguments (list or None): Command-line arguments to pass to the
            module.

    Returns:
        tuple[str, int]: A 2-tuple of ``(output, return_code)`` where
            ``output`` is the combined stdout/stderr text and ``return_code``
            is the process exit code (0 on success).

    Raises:
        DAError: If ``arguments`` is not a list.
    """
    ...

def undefine(*args: Any, **kwargs: Any) -> Any: ...
def invalidate(*args: Any, **kwargs: Any) -> Any: ...
def dispatch(*args: Any, **kwargs: Any) -> Any: ...
def yesno(*args: Any, **kwargs: Any) -> Any: ...
def noyes(*args: Any, **kwargs: Any) -> Any: ...
def split(*args: Any, **kwargs: Any) -> Any: ...
def showif(*args: Any, **kwargs: Any) -> Any: ...
def showifdef(*args: Any, **kwargs: Any) -> Any: ...
def phone_number_part(*args: Any, **kwargs: Any) -> Any: ...
def pdf_concatenate(*pargs: Any, **kwargs: Any) -> Any:
    """
    Concatenate PDF files into a single PDF file.

    Args:
        *pargs: DAFile, DAFileList, DAFileCollection, DAStaticFile, or path
            strings representing the PDF files to concatenate.
        **kwargs: Optional keyword arguments:
            - ``output_to`` (DAFile or None): Target file to write into.
            - ``filename`` (str): Filename for the resulting file. Defaults
              to ``'file.pdf'``.
            - ``pdfa`` (bool): If True, convert to PDF/A.
            - ``password`` (str, list, or dict): Password(s) to apply to the
              output PDF.

    Returns:
        DAFile: The concatenated PDF file.

    Raises:
        DAError: If no valid files are provided, or ``output_to`` is not a
            DAFile.
    """
    ...

def set_parts(*args: Any, **kwargs: Any) -> Any: ...
def log(*args: Any, **kwargs: Any) -> Any: ...
def encode_name(*args: Any, **kwargs: Any) -> Any: ...
def decode_name(*args: Any, **kwargs: Any) -> Any: ...
def interview_list(*args: Any, **kwargs: Any) -> Any: ...
def interview_menu(*args: Any, **kwargs: Any) -> Any: ...
def server_capabilities(*args: Any, **kwargs: Any) -> Any: ...
def session_tags(*args: Any, **kwargs: Any) -> Any: ...
def include_docx_template(*args: Any, **kwargs: Any) -> Any: ...
def get_chat_log(*args: Any, **kwargs: Any) -> Any: ...
def get_user_list(*args: Any, **kwargs: Any) -> Any: ...
def get_user_info(*args: Any, **kwargs: Any) -> Any: ...
def set_user_info(*args: Any, **kwargs: Any) -> Any: ...
def get_user_secret(*args: Any, **kwargs: Any) -> Any: ...
def create_user(*args: Any, **kwargs: Any) -> Any: ...
def invite_user(*args: Any, **kwargs: Any) -> Any: ...
def create_session(*args: Any, **kwargs: Any) -> Any: ...
def get_session_variables(*args: Any, **kwargs: Any) -> Any: ...
def set_session_variables(*args: Any, **kwargs: Any) -> Any: ...
def go_back_in_session(*args: Any, **kwargs: Any) -> Any: ...
def manage_privileges(*args: Any, **kwargs: Any) -> Any: ...
def start_time(timezone: Any = ...) -> Any:
    """
    Return the time the current interview session was started.

    Args:
        timezone (str or None): IANA timezone name for the returned datetime.
            If None, UTC is used.

    Returns:
        DADateTime: Session start time.
    """
    ...

def zip_file(*pargs: Any, **kwargs: Any) -> Any:
    """
    Create a ZIP archive from the provided files and return it as a DAFile.

    Args:
        *pargs: Files to include. Each argument may be a DAFile, DAFileList,
            DAFileCollection, DAStaticFile, or a dict mapping folder names to
            files.
        **kwargs: Optional keyword arguments:
            - ``output_to`` (DAFile or None): Target DAFile to write into.
            - ``filename`` (str): Filename for the ZIP archive. Defaults to
              ``'file.zip'``.

    Returns:
        DAFile: The ZIP archive file.
    """
    ...

def validation_error(the_message: Any, field: Any = ...) -> Any:
    """
    Raise a validation error to reject a field value in the interview.

    Args:
        the_message (str): Human-readable message to display to the user.
        field (str or None): Field variable name to associate the error with.
            If None, the error applies to the entire question.

    Raises:
        DAValidationError: Always raised with the given message and field.
    """
    ...

DAValidationError: Any

def redact(*args: Any, **kwargs: Any) -> Any: ...
def forget_result_of(*args: Any, **kwargs: Any) -> Any: ...
def re_run_logic(*args: Any, **kwargs: Any) -> Any: ...
def reconsider(*args: Any, **kwargs: Any) -> Any: ...
def action_button_html(
    url: Any,
    icon: Any = ...,
    color: Any = ...,
    size: Any = ...,
    block: Any = ...,
    label: Any = ...,
    classname: Any = ...,
    new_window: Any = ...,
    id_tag: Any = ...,
) -> Any:
    """
    Return HTML for a Bootstrap button that links to a URL.

    Args:
        url (str): The URL the button navigates to.
        icon (str or None): Font Awesome icon name (e.g. ``'pencil'``).
        color (str): Bootstrap color variant (e.g. ``'success'``,
            ``'danger'``, ``'primary'``). Defaults to ``'success'``.
        size (str): Bootstrap button size — ``'sm'``, ``'md'``, or ``'lg'``.
            Defaults to ``'sm'``.
        block (bool): If True, make the button full-width. Defaults to False.
        label (str): Button label text. Defaults to ``'Edit'``.
        classname (str or None): Additional CSS class(es) to add to the button.
        new_window (bool, str, or None): If True, open in a new tab/window;
            if a string, use it as the ``target`` attribute value.
        id_tag (str or None): HTML ``id`` attribute for the button.

    Returns:
        str: HTML ``<a>`` element styled as a Bootstrap button.
    """
    ...

def url_ask(data: Any) -> Any:
    """
    Return a URL that, when visited, seeks a sequence of variables.

    Similar to ``url_action``, but accepts a structured list describing which
    variables to seek, undefine, invalidate, recompute, or set.

    Args:
        data (str, dict, or list): A variable name, a control dict (with
            ``'undefine'``, ``'invalidate'``, ``'recompute'``, ``'set'``, or
            ``'follow up'`` keys), an action dict (with ``'action'`` and
            ``'arguments'`` keys), or a list combining any of the above.

    Returns:
        str: URL that drives the interview to seek the requested variables.

    Raises:
        DAError: If variable names are invalid or the data structure is
            malformed.
    """
    ...

def overlay_pdf(
    main_pdf: Any,
    logo_pdf: Any,
    first_page: Any = ...,
    last_page: Any = ...,
    logo_page: Any = ...,
    only: Any = ...,
    multi: Any = ...,
    output_to: Any = ...,
    filename: Any = ...,
) -> Any:
    """
    Overlay pages from one PDF on top of the pages of another PDF.

    Args:
        main_pdf (DAFile, DAFileCollection, DAFileList, or str): The base PDF.
        logo_pdf (DAFile, DAFileCollection, DAFileList, or str): The PDF whose
            pages are stamped on top of ``main_pdf``.
        first_page (int or None): First page of ``main_pdf`` to stamp.
        last_page (int or None): Last page of ``main_pdf`` to stamp.
        logo_page (int or None): Page from ``logo_pdf`` to use as the stamp.
        only (int or None): Single page of ``main_pdf`` to stamp.
        multi (bool): If True, cycle through all pages of ``logo_pdf`` when
            stamping.
        output_to (DAFile or None): Target DAFile for the result. A new
            DAFile is created if None.
        filename (str or None): Filename for the output file. Defaults to
            ``'file.pdf'``.

    Returns:
        DAFile: The stamped PDF file.

    Raises:
        DAError: If the PDF references are invalid or ``output_to`` is not a
            DAFile.
    """
    ...

def get_question_data(*args: Any, **kwargs: Any) -> Any: ...
def set_title(*args: Any, **kwargs: Any) -> Any: ...
def set_save_status(*args: Any, **kwargs: Any) -> Any: ...
def single_to_double_newlines(*args: Any, **kwargs: Any) -> Any: ...

class RelationshipTree(DAObject):
    """
    A data structure that maps directed and peer relationships among objects.

    Maintains two collections: ``relationships_dir`` for directed parent/child
    relationships and ``relationships_peer`` for undirected peer relationships.
    Supports filtering queries via keyword arguments or filter functions.

    Attributes:
        leaf (DAList): Collection of all nodes (people or objects) tracked by
            this tree.
        relationships_dir (DAList): Collection of directed
            ``RelationshipDir`` objects.
        relationships_peer (DAList): Collection of undirected
            ``RelationshipPeer`` objects.
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def new(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _func_list(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _and(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _or(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def query_peer(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Query peer relationships using a filter function or keyword match.

        Args:
            *pargs: Optional single filter function accepting a
                ``RelationshipPeer`` and returning bool.
            **kwargs: A single keyword argument used to build a filter
                automatically (e.g. ``involves=person``).

        Returns:
            generator: A generator of ``RelationshipPeer`` objects that match
                the filter.

        Raises:
            DAError: If the query arguments cannot be resolved to a valid
                filter function.
        """
        ...
    def query_dir(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Query directed relationships using a filter function or keyword match.

        Args:
            *pargs: Optional single filter function accepting a
                ``RelationshipDir`` and returning bool.
            **kwargs: A single keyword argument used to build a filter
                automatically (e.g. ``parent=person``).

        Returns:
            generator: A generator of ``RelationshipDir`` objects that match
                the filter.

        Raises:
            DAError: If the query arguments cannot be resolved to a valid
                filter function.
        """
        ...
    def add_relationship_dir(self, parent: Any = ..., child: Any = ..., relationship_type: Any = ...) -> Any:
        """
        Add or retrieve a directed (parent/child) relationship.

        Args:
            parent: The parent node of the relationship.
            child: The child node of the relationship.
            relationship_type: An identifier for the type of relationship.

        Returns:
            RelationshipDir: The existing or newly created relationship object.
        """
        ...
    def delete_dir(self, *pargs: Any) -> Any:
        """
        Delete one or more directed relationships from the tree.

        Args:
            *pargs: The ``RelationshipDir`` objects to remove.
        """
        ...
    def add_relationship_peer(self, *pargs: Any, **kwargs: Any) -> Any:
        """
        Add or retrieve an undirected (peer) relationship among nodes.

        Args:
            *pargs: The nodes that are peers in this relationship.
            relationship_type: Keyword argument identifying the type of
                relationship.

        Returns:
            RelationshipPeer: The existing or newly created peer relationship.
        """
        ...
    def delete_peer(self, *pargs: Any) -> Any:
        """
        Delete one or more peer relationships from the tree.

        Args:
            *pargs: The ``RelationshipPeer`` objects to remove.
        """
        ...

class DAContext(DADict):
    """
    A context-sensitive value that renders differently depending on the output format.

    When converted to a string, the value appropriate for the current output
    context (``question``, ``docx``, ``pdf``, ``pandoc``, or ``document``) is
    returned.

    Attributes:
        question (str): Text used in interview questions (default context).
        document (str): Text used in PDF and DOCX document contexts when no
            more-specific key is present.
        docx (str): Text used in DOCX documents (overrides ``document``).
        pdf (str): Text used in PDF documents (overrides ``document``).
        pandoc (str): Text used in Pandoc-rendered documents (overrides
            ``document``).
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __str__(self) -> Any: ...
    def __repr__(self) -> Any: ...
    def __hash__(self) -> Any: ...

class DAOAuth(DAObject):
    """
    A base class for performing OAuth2 authorization flows within an interview.

    Attributes:
        url_args (dict): URL query parameters received from the OAuth2
            callback (must be passed as a keyword argument at construction).
    """
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def _get_flow(self) -> Any: ...
    def _setup(self) -> Any: ...
    def _get_redis_key(self) -> Any: ...
    def _get_redis_cred_storage(self) -> Any: ...
    def _get_random_unique_id(self) -> Any: ...
    def get_credentials(self) -> Any:
        """Returns the stored credentials."""
        ...
    def delete_credentials(self) -> Any:
        """Deletes the stored credentials."""
        ...
    def get_http(self) -> Any:
        """Returns an http object that can be used to communicate with the OAuth-enabled API."""
        ...
    def authorize(self, web: Any) -> Any:
        """Adds the appropriate headers to a DAWeb object"""
        ...
    def ensure_authorized(self) -> Any:
        """If the credentials are not valid, starts the authorization process."""
        ...
    def active(self) -> Any:
        """Returns True if user has stored credentials, whether they are valid or not.  Otherwise returns False."""
        ...
    def is_authorized(self) -> Any:
        """Returns True if user has stored credentials and the credentials are valid."""
        ...

class DAStore(DAObject):
    """
    A key-value store backed by server-side SQL, with optional encryption.

    Attributes:
        base (str): Storage scope — ``'user'`` (per-user, encrypted),
            ``'interview'`` (per-interview, unencrypted), ``'session'``
            (per-session, encrypted), ``'global'`` (site-wide, unencrypted),
            or a custom string prefix. Defaults to ``'user'``.
        encrypted (bool): If set, overrides the default encryption behavior
            for the chosen ``base``.
    """
    def is_encrypted(self) -> Any:
        """
        Return True if data is stored with encryption.

        Returns:
            bool: True if encryption is enabled for this store.
        """
        ...
    def _get_base_key(self) -> Any: ...
    def defined(self, key: Any) -> Any:
        """
        Return True if the given key exists in the store.

        Args:
            key (str): Key to check.

        Returns:
            bool: True if the key exists; False otherwise.
        """
        ...
    def get(self, key: Any) -> Any:
        """
        Retrieve the value stored under the given key.

        Args:
            key (str): Key to retrieve.

        Returns:
            object: The stored value, or None if not found.
        """
        ...
    def set(self, key: Any, the_value: Any) -> Any:
        """
        Store a value under the given key.

        Args:
            key (str): Key under which to store the value.
            the_value (object): Value to store.
        """
        ...
    def delete(self, key: Any) -> Any:
        """
        Delete the value stored under the given key.

        Args:
            key (str): Key to delete.
        """
        ...
    def keys(self) -> Any:
        """
        Return a list of all keys currently stored.

        Returns:
            list[str]: Keys present in this store.
        """
        ...

def explain(the_explanation: Any, category: Any = ...) -> Any:
    """
    Add an explanation string to the session's explanation history.

    Args:
        the_explanation (str): The explanation text to record.
        category (str): Category name for grouping explanations. Defaults to
            ``'default'``.
    """
    ...

def clear_explanations(category: Any = ...) -> Any:
    """
    Clear the session's explanation history.

    Args:
        category (str): Category to clear, or ``'all'`` to clear every
            category. Defaults to ``'default'``.
    """
    ...

def logic_explanation(category: Any = ...) -> Any:
    """
    Return the list of recorded explanations for a category.

    Args:
        category (str): Category name. Defaults to ``'default'``.

    Returns:
        list[str]: Explanation strings recorded for the category, in order.
    """
    ...

def set_status(**kwargs: Any) -> Any:
    """
    Set miscellaneous key-value status settings for the interview session.

    Args:
        **kwargs: Arbitrary key-value pairs to store in the session's internal
            ``'misc'`` dictionary.
    """
    ...

def get_status(setting: Any) -> Any:
    """
    Retrieve a miscellaneous status setting for the interview session.

    Args:
        setting (str): The key to look up.

    Returns:
        object or None: The stored value, or None if the key does not exist.
    """
    ...

def verbatim(*args: Any, **kwargs: Any) -> Any: ...

add_separators: Any

class DAWeb(DAObject):
    """
    An HTTP client for calling external REST APIs from an interview.

    Attributes:
        base_url (str): Base URL prepended to relative paths passed to HTTP
            methods.
        headers (dict): Default request headers merged into every call.
        cookies (dict): Default cookies sent with every call and updated from
            each response.
        auth (dict): Authentication credentials. The ``type`` key selects the
            scheme (``'basic'``, ``'digest'``, or ``'bearer'``).
        json_body (bool): If True (the default), POST/PUT/PATCH bodies are
            sent as JSON; otherwise as form-encoded data.
        on_failure: Default value returned (or exception raised) when a
            request fails. Use ``'raise'`` to raise a ``DAWebError``.
        on_success: Default value returned on success. By default the parsed
            JSON response (or raw text) is returned.
        success_code (int or list[int]): HTTP status code(s) considered
            successful. Defaults to any 2xx code.
        task (str): Interview task name to mark as performed on success.
    """
    def _get_base_url(self) -> Any: ...
    def _get_on_failure(self, on_failure: Any) -> Any: ...
    def _get_success_code(self, success_code: Any) -> Any: ...
    def _get_on_success(self, on_success: Any) -> Any: ...
    def _get_task(self, task: Any) -> Any: ...
    def _get_task_persistent(self, task_persistent: Any) -> Any: ...
    def _get_auth(self, auth: Any) -> Any: ...
    def _get_headers(self, new_headers: Any) -> Any: ...
    def _get_cookies(self, new_cookies: Any) -> Any: ...
    def _get_json_body(self, json_body: Any) -> Any: ...
    def _call(
        self,
        url: Any,
        method: Any = ...,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
        files: Any = ...,
        cookies: Any = ...,
        success_code: Any = ...,
    ) -> Any: ...
    def get(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
    ) -> Any:
        """
        Send an HTTP GET request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Query parameters (merged with ``params``).
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): Ignored for GET (no body).
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success (default: parsed JSON or text).
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...
    def post(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
        files: Any = ...,
    ) -> Any:
        """
        Send an HTTP POST request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Request body data.
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): If True (default), send body as JSON.
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success.
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.
            files (dict): Files to upload, mapping field names to file objects.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...
    def put(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
        files: Any = ...,
    ) -> Any:
        """
        Send an HTTP PUT request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Request body data.
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): If True (default), send body as JSON.
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success.
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.
            files (dict): Files to upload.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...
    def patch(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
        files: Any = ...,
    ) -> Any:
        """
        Send an HTTP PATCH request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Request body data.
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): If True (default), send body as JSON.
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success.
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.
            files (dict): Files to upload.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...
    def delete(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
    ) -> Any:
        """
        Send an HTTP DELETE request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Query parameters.
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): Ignored for DELETE.
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success.
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...
    def options(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
    ) -> Any:
        """
        Send an HTTP OPTIONS request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Query parameters.
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): Ignored for OPTIONS.
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success.
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...
    def head(
        self,
        url: Any,
        data: Any = ...,
        params: Any = ...,
        headers: Any = ...,
        json_body: Any = ...,
        on_failure: Any = ...,
        on_success: Any = ...,
        auth: Any = ...,
        cookies: Any = ...,
        task: Any = ...,
        task_persistent: Any = ...,
    ) -> Any:
        """
        Send an HTTP HEAD request.

        Args:
            url (str): Target URL or path relative to ``base_url``.
            data (dict): Query parameters.
            params (dict): URL query parameters.
            headers (dict): Additional request headers.
            json_body (bool): Ignored for HEAD.
            on_failure: Value to return on failure, or ``'raise'``.
            on_success: Value to return on success.
            auth: Authentication credentials.
            cookies (dict): Additional cookies.
            task (str): Task name to mark as performed on success.
            task_persistent (bool): If True, the task persists across sessions.

        Returns:
            object: Parsed JSON response, raw text, or the ``on_failure``/
                ``on_success`` value.
        """
        ...

DAWebError: Any

json: Any

re: Any

def iso_country(country: Any, part: Any = ...) -> Any:
    """
    Return ISO 3166-1 country data for a given country name or code.

    Args:
        country (str): Country name or code (fuzzy-matched with
            ``pycountry``).
        part (str): The field to return — ``'alpha_2'`` (default),
            ``'alpha_3'``, ``'name'``, ``'official_name'``, or
            ``'numeric'``.

    Returns:
        str: Requested field value for the matched country.

    Raises:
        DAError: If the country cannot be found or the ``part`` is
            unrecognized.
    """
    ...

def assemble_docx(
    input_file: Any,
    fields: Any = ...,
    output_path: Any = ...,
    output_format: Any = ...,
    return_content: Any = ...,
    pdf_options: Any = ...,
    filename: Any = ...,
) -> Any:
    """
    Render a DOCX template file and return or save the result.

    Args:
        input_file (DAFile, DAStaticFile, or str): The DOCX template file.
        fields (dict or None): Extra variables to pass to the Jinja2 template.
            Defaults to the current interview's variable dictionary.
        output_path (str or None): Filesystem path to write the output.
            If None, a temporary file is used.
        output_format (str): ``'docx'``, ``'pdf'``, or ``'md'``. Defaults to
            ``'docx'``.
        return_content (bool): If True, return the file contents as bytes
            (or str for ``'md'``) instead of a path. Defaults to False.
        pdf_options (dict or None): PDF conversion options when
            ``output_format`` is ``'pdf'`` (keys: ``pdfa``, ``password``,
            ``owner_password``, ``update_refs``, ``tagged``).
        filename (str or None): Filename hint passed to the PDF converter.

    Returns:
        str or bytes or None: File path (str) when a temporary file is used
            and ``return_content`` is False; file contents (bytes or str)
            when ``return_content`` is True; None when ``output_path`` is
            specified.

    Raises:
        DAError: If the input file is missing, the format is invalid, or
            conversion fails.
    """
    ...

def docx_concatenate(*pargs: Any, **kwargs: Any) -> Any:
    """
    Concatenate DOCX files into a single DOCX file.

    Args:
        *pargs: DAFile, DAFileList, DAStaticFile, or path strings to
            concatenate.
        **kwargs: Optional keyword arguments:
            - ``output_to`` (DAFile or None): Target file to write into.
            - ``filename`` (str): Filename for the resulting file. Defaults
              to ``'file.docx'``.

    Returns:
        DAFile: The concatenated DOCX file.

    Raises:
        DAError: If no valid files are provided, or ``output_to`` is not a
            DAFile.
    """
    ...

def store_variables_snapshot(*args: Any, **kwargs: Any) -> Any: ...
def stash_data(data: Any, expire: Any = ...) -> Any:
    """
    Store data in encrypted form and return a retrieval key and secret.

    Args:
        data (object): Picklable Python object to stash.
        expire (int or None): TTL in seconds. Defaults to 90 days.

    Returns:
        tuple[str, str]: ``(stash_key, secret)`` — pass both to
            :func:`retrieve_stashed_data` to recover the data.

    Raises:
        DAError: If ``expire`` is not a positive integer.
    """
    ...

def retrieve_stashed_data(stash_key: Any, secret: Any, delete: Any = ..., refresh: Any = ...) -> Any:
    """
    Retrieve data previously stored with :func:`stash_data`.

    Args:
        stash_key (str): Key returned by :func:`stash_data`.
        secret (str): Decryption secret returned by :func:`stash_data`.
        delete (bool): If True, delete the stash after retrieval. Defaults to
            False.
        refresh (bool or int): If True, reset the TTL to 90 days. If a
            positive integer, reset the TTL to that many seconds.

    Returns:
        object: The original stashed Python object, or None if not found.
    """
    ...

def update_terms(*args: Any, **kwargs: Any) -> Any: ...

chain: Any

class DABreadCrumbs(DAObject):
    """A breadcrumb navigation widget for multi-step interviews."""
    def get_crumbs(self) -> Any:
        """
        Return the breadcrumb trail for the current interview action stack.

        Returns:
            list[dict]: List of dicts with ``'breadcrumb'`` keys, representing
                parent questions followed by the current question.
        """
        ...
    def show(self) -> Any:
        """
        Return HTML for the breadcrumb navigation element.

        Returns:
            str: HTML ``<nav>`` breadcrumb element, or an empty string if
                there are fewer than two crumbs.
        """
        ...
    def container(self, items: Any) -> Any:
        """
        Return the HTML container wrapping the breadcrumb items.

        Args:
            items (iterable[str]): HTML strings for each breadcrumb item.

        Returns:
            str: HTML ``<nav>`` element containing an ordered list.
        """
        ...
    def inner(self, label: Any, active: Any) -> Any:
        """
        Return the HTML for a single breadcrumb item.

        Args:
            label (str): Display label for the breadcrumb.
            active (bool): If True, mark the item as the current (active)
                page.

        Returns:
            str: HTML ``<li>`` element for the breadcrumb.
        """
        ...

def set_variables(*args: Any, **kwargs: Any) -> Any: ...
def language_name(*args: Any, **kwargs: Any) -> Any: ...

DA: Any

class DAGlobal(DAObject):
    """
    An object whose attributes are persisted in unencrypted global storage outside the interview session.

    Attributes saved on this object are written to a server-side SQL store keyed
    by ``base`` and ``key``, and are restored automatically each time the object
    is unpickled.

    Attributes:
        base (str): Storage scope — ``'user'`` (per-user), ``'interview'``
            (per-interview), or ``'global'`` (site-wide). Defaults to
            ``'user'``.
        key (str): Unique identifier for this object within the chosen base.
            Defaults to a random 32-character alphanumeric string.
    """
    @classmethod
    def keys(cls, base: Any) -> Any: ...
    @classmethod
    def defined(cls, base: Any, key: Any) -> Any:
        """
        Return True if a DAGlobal value exists for the given base and key.

        Args:
            base (str): Storage scope (``'user'``, ``'interview'``, or
                ``'global'``).
            key (str): The key to look up.

        Returns:
            bool: True if the key exists; False otherwise.
        """
        ...
    @classmethod
    def remove(cls, base: Any, key: Any) -> Any:
        """
        Delete the stored value for the given base and key.

        Args:
            base (str): Storage scope (``'user'``, ``'interview'``, or
                ``'global'``).
            key (str): The key to delete.
        """
        ...
    def init(self, *pargs: Any, **kwargs: Any) -> Any: ...
    def __getstate__(self) -> Any: ...
    def __setstate__(self, pickle_dict: Any) -> Any: ...
    def delete(self) -> Any:
        """Delete all data from global storage and undefine all object attributes."""
        ...

def run_action_in_session(*args: Any, **kwargs: Any) -> Any: ...
def transform_json_variables(obj: Any) -> Any:
    """
    Transform an object's docassemble variables into a JSON-serializable form.

    Args:
        obj (object): Python object (may contain DAObject instances, dates,
            etc.) to transform.

    Returns:
        object: A JSON-serializable version of ``obj``, with docassemble types
            converted to their plain Python equivalents.
    """
    ...
