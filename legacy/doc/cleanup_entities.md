# Cleanup unavailable entities

After migrating to the 2026 version of this integration, some entities were removed. If you want to cleanup your installation follow these steps:

## Find and delete unavailable entities

- Go to ```Settings --> Devices & Services --> Tab: Entities```
- Adjust filters (top left, see screenshots below): 
    - ```Status --> Unavailable ```
    - ```Intgrations --> Modbus```
- Click on the icon left to the search bar: ```Enter selection mode```
- Select the entities you want to remove and click on the three dots icon (top right) --> ```Delete selected entities```
- Restart Home Assistant to finalize the cleanup.


<figure>
  <img src="images/unavailable_entities_filter_integrations.drawio.svg" width="600">
  <figcaption>Filter entities by integration</figcaption>
</figure>


<figure>
  <img src="images/unavailable_entities_filter_status.drawio.svg" width="600">
  <figcaption>Filter entities by status</figcaption>
</figure>


<figure>
  <img src="images/unavailable_entities_selection.drawio.svg" width="600">
  <figcaption>Select entities to delete</figcaption>
</figure>


<figure>
  <img src="images/unavailable_entities_delete.drawio.svg" width="600">
  <figcaption>Delete entities</figcaption>
</figure>