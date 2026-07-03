import frappe
from frappe import _
from frappe.query_builder import DocType, Order


@frappe.whitelist(allow_guest=True)
def get_available_properties():
	try:
		Property = DocType("Utility Property")
		FeatureItem = DocType("Utility Property Feature item")
		GalleryImage = DocType("Property Gallery Image")

		properties = (
			frappe.qb.from_(Property)
			.select(
				Property.name,
				Property.property_name,
				Property.utility_category,
				Property.company,
				Property.status,
				Property.is_fixed_asset,
				Property.is_group,
				Property.location,
				Property.territory,
				Property.house_no,
				Property.plot_no,
				Property.lot_size,
				Property.unit_number,
				Property.bedrooms,
				Property.bathrooms,
				Property.unit_type,
				Property.unit_size,
				Property.floor_level,
				Property.cover_image,
				Property.unique_features,
				Property.legal_description,
				Property.asset_category,
				Property.purchase_date,
				Property.net_purchase_amount,
				Property.parent_utility_property,
			)
			.where(Property.status == "Available")
			.where(Property.is_group == 0)
			.orderby(Property.creation, order=Order.desc)
			.run(as_dict=True)
		)

		if not properties:
			return {"message": []}

		property_names = [p.name for p in properties]

		if property_names:
			features = (
				frappe.qb.from_(FeatureItem)
				.select(FeatureItem.parent, FeatureItem.feature, FeatureItem.feature_type, FeatureItem.notes)
				.where(FeatureItem.parent.isin(property_names))
				.run(as_dict=True)
			)

			gallery_images = (
				frappe.qb.from_(GalleryImage)
				.select(GalleryImage.parent, GalleryImage.image, GalleryImage.title, GalleryImage.description)
				.where(GalleryImage.parent.isin(property_names))
				.run(as_dict=True)
			)

			feature_map = {}
			for feature in features:
				if feature.parent not in feature_map:
					feature_map[feature.parent] = []
				feature_map[feature.parent].append(
					{"feature": feature.feature, "feature_type": feature.feature_type, "notes": feature.notes}
				)

			gallery_map = {}
			for image in gallery_images:
				if image.parent not in gallery_map:
					gallery_map[image.parent] = []
				gallery_map[image.parent].append(
					{"image": image.image, "title": image.title, "description": image.description}
				)

			for property in properties:
				if property.name in feature_map:
					property["features"] = feature_map[property.name]
				if property.name in gallery_map:
					property["image_gallery"] = gallery_map[property.name]

		return {"message": properties}

	except Exception as e:
		frappe.log_error(f"Error fetching properties: {str(e)}", "Property Listing API")
		return {"message": [], "error": str(e)}
