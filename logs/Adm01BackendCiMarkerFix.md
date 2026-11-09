# ADM-01 CI ordering-marker fix ? 2026-11-10

Random hex marker tags could contain long numeric runs that the phone-number privacy detector correctly redacted, making the ordering assertion intermittently see None. Quality-test marker tags now use alphabetic encodings; all newest-first, item-count and privacy assertions remain unchanged. No production privacy controls changed. No tests run, as requested.
