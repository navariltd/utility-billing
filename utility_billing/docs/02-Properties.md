# Properties

A **Utility Property** is either a building (a group) or a lettable unit — an
apartment, house, office or shop. Units are what tenants rent, what contracts
list and what gets billed.

![Utility Property](./images/utility_property.png)

## Add a building

1. Go to **Utility Property → New**.
2. Enter a **Name** — it must be unique. Use the name people recognise, for
   example _The Pinnacle Towers - Kilimani_.
3. Tick **Is Group** to mark it as a building that holds units.
4. Choose the **Company** and, if you use them, the **Territory** and
   **Utility Category**.
5. Add the address and contact records on the **Address & Contacts** tab.
6. Save.

## Add the units inside it

1. Create another **Utility Property**, this time leaving **Is Group**
   unticked.
2. Set **Parent Utility Property** to the building, or simply pick the building
   in the property tree and add a child.
3. Fill in the unit details below.
4. Set **Availability Status** — _Available_, _Reserved_, _Occupied_ or _Under
   Maintenance_.
5. Save.

Repeat for every unit. Tenants can then be offered individual units, and each
unit is billed on its own.

## What each section is for

### Unit information

| Field                    | What to enter                                                      |
| ------------------------ | ------------------------------------------------------------------ |
| **Unit Number**          | The door or suite number, e.g. `A-101`                             |
| **Unit Type**            | Studio, one/two/three bedroom, office, shop — maintained as a link |
| **Bedrooms / Bathrooms** | Used by the portal and the availability report                     |
| **Floor Level**          | Where the unit sits in the building                                |
| **Unit Size (sqft)**     | Lettable area                                                      |

### Location details

| Field                    | What to enter                     |
| ------------------------ | --------------------------------- |
| **Location**             | The estate, neighbourhood or site |
| **Territory**            | Sales territory, for reporting    |
| **House No / Plot No**   | Street address identifiers        |
| **Lot Size (Land Area)** | Land area, for houses and plots   |

### Features and amenities

List what makes the unit attractive — parking, borehole water, balcony, backup
generator, gym access. Each row is one feature, and the list is shown on the
rental portal so prospective tenants can compare units.

### Gallery

- **Cover Image** — the picture used on the portal card.
- **Image Gallery** — additional photos of the unit or building.

Both are optional; the portal falls back to a styled placeholder when no image
is set.

### Asset details (optional)

Tick **Is Fixed Asset** when the property is also tracked as a company asset.
Then choose the **Asset Category**, the linked **Item**, the **Asset Naming
Series** and the **Net Purchase Amount**. If you pick an item that is already a
fixed asset, the category and amount are filled from it and become read only.

> The rent **Service Item** is filled automatically when _Auto Create Property
> Service Item_ is enabled in [Settings](./01-Settings.md). It is the item used
> to bill rent for this property; see
> [Rent Billing](./08-Rent-Billing.md). Group properties are never given a rent
> item — only lettable units are billed.

## Keeping the list usable

- Group properties so the tree mirrors the real estate: building → floor →
  unit. Filter or expand the tree instead of scrolling a long list.
- Keep **Availability Status** current. The portal only offers _Available_
  units, and the availability report counts the rest.
- Add the gallery before publishing a unit, so the booking page looks complete.
- Never reuse a unit name for a different unit — contracts and invoices point at
  the property by name.

## If something does not work

- **A unit is not offered on the portal** — check its status is _Available_ and
  that it is not a group.
- **Rent cannot be billed for a unit** — the property has no service item. Save
  the property again with _Auto Create Property Service Item_ enabled.
- **A building is offered as a unit** — it still has **Is Group** unticked. Tick
  it so the building is treated as a container and only its units are let.

---
