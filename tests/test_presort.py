from datetime import timedelta

from triage.stages.presort import presort

from .conftest import NOW


def test_counts_dedupes_and_rule_categories(mailbox):
    emails = mailbox.fetch_since(NOW - timedelta(hours=24), 500)
    result = presort(emails, newsletter_senders=["flipboard.com"], ignore_senders=["spammy.example"])

    assert result.total == 7  # m0 is outside the window, the second m1 is a duplicate
    assert result.duplicates == 1
    assert result.ignored == 1
    assert result.sender_counts["Sam Okafor"] == 1
    cats = {i.email.id: i.known_category for i in result.items}
    assert cats["m3"] == "newsletter"  # listed sender
    assert cats["m4"] == "promotion"  # Gmail label
    assert cats["m7"] == "social"
    assert cats["m2"] is None  # job alert has an unsubscribe header but still goes to the model
    assert cats["m1"] is None and cats["m5"] is None
