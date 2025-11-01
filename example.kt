package com.citymapper.app.via.common.api

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

/* Represents an Endpoint (origin/destination) location in Via API models */
@JsonClass(generateAdapter = true)
data class ViaApiStop(
  @Json(name = "full_geocoded_addr")
  val fullGeocodedAddr: String?,
  @Json(name = "geocoded_addr")
  val geocodedAddr: String?,
  @Json(name = "latlng")
  val latlng: ViaApiLatLng,
  @Json(name = "is_manually_selected")
  val isManuallySelected: Boolean? = false
)
