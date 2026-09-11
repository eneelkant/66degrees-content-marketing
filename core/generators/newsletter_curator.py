from ._specialist import SpecialistScaffoldStrategy
class NewsletterCuratorStrategy(SpecialistScaffoldStrategy):
    asset_type = "newsletter"
    section_name = "Newsletter Lead"
    default_title_suffix = "Newsletter"
