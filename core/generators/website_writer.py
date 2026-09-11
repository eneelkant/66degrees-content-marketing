from ._specialist import SpecialistScaffoldStrategy
class WebsiteWriterStrategy(SpecialistScaffoldStrategy):
    asset_type = "website"
    section_name = "Page Value Proposition"
    default_title_suffix = "Website Content"
