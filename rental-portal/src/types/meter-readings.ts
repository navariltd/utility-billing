/**
 * Types returned by `utility_billing.api.portal.meter_readings`.
 */

/** A meter line of a reading: one meter, one item, one consumption. */
export interface MeterReadingItem {
  name: string;
  parent: string;
  item_code: string | null;
  item_name: string | null;
  meter_number: string | null;
  uom: string | null;
  previous_reading: number;
  current_reading: number;
  consumption: number;
}

/** A `Meter Reading` recorded for one of the caller's units. */
export interface MeterReadingRow {
  name: string;
  date: string | null;
  customer: string;
  customer_name: string | null;
  property: string | null;
  property_label: string | null;
  company: string | null;
  currency: string | null;
  price_list: string | null;
  docstatus: number;
  items: MeterReadingItem[];
  total_consumption: number;
  total_amount: number;
}

/** One tariff block of a reading: how much was billed at which rate. */
export interface MeterReadingRate {
  parent: string;
  meter_reading_item: string | null;
  item_code: string | null;
  item_name: string | null;
  meter_number: string | null;
  uom: string | null;
  block: string | null;
  qty: number;
  rate: number;
  amount: number;
}

/** A single reading returned by `get_customer_meter_reading`. */
export interface MeterReadingDetail extends MeterReadingRow {
  rates: MeterReadingRate[];
  totals: {
    consumption: number;
    amount: number;
    blocks: number;
  };
}

/** Payload returned by `get_customer_meter_readings`. */
export interface CustomerMeterReadings {
  customer: string | null;
  customers: { name: string; customer_name: string }[];
  meter_readings: MeterReadingRow[];
  properties: {
    name: string;
    property_name: string | null;
    unit_number: string | null;
    house_no: string | null;
    plot_no: string | null;
  }[];
  totals: {
    readings: number;
    consumption: number;
    amount: number;
    currency: string | null;
    latest_date: string | null;
  };
}

