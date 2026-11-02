// Create a Text parameter named PackageFolder pointing to the package directory.
// Create one blank query named LoadCsv with this function:
(FileName as text, ColumnTypes as list) as table =>
let
    Root = Text.TrimEnd(PackageFolder, {"\", "/"}),
    Raw = Csv.Document(File.Contents(Root & "\" & FileName), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Raw, [PromoteAllScalars=true]),
    Blanks = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, Table.ColumnNames(Headers)),
    Typed = Table.TransformColumnTypes(Blanks, ColumnTypes, "en-US")
in Typed

// The expressions below are SEPARATE named queries, not one script.
// Query name: DimDate
LoadCsv("dim_date.csv", {{"date", type date}})

// Query name: DimDevice
LoadCsv("dim_device.csv", {{"device_category", type text}})

// Query name: DimStage
LoadCsv("dim_stage.csv", {{"stage_order", Int64.Type}, {"stage", type text}, {"stage_label", type text}})

// Query name: DailyKpis
LoadCsv("daily_kpis.csv", {{"activity_date", type date}, {"event_count", Int64.Type}, {"daily_active_users", Int64.Type}, {"daily_active_sessions", Int64.Type}, {"entry_cohort_sessions", Int64.Type}, {"missing_source_events", Int64.Type}, {"missing_source_rate", type number}, {"missing_medium_events", Int64.Type}, {"missing_medium_rate", type number}})

// Query name: AuditOverallFunnel
LoadCsv("overall_ordered_funnel.csv", {{"stage", type text}, {"stage_order", Int64.Type}, {"ordered_sessions", Int64.Type}, {"ordered_unique_users", Int64.Type}, {"conversion_from_product_view_rate", type number}, {"step_conversion_rate", type number}, {"abandoned_sessions", Int64.Type}, {"step_abandonment_rate", type number}, {"product_view_denominator", Int64.Type}, {"previous_stage_denominator", Int64.Type}, {"stage_label", type text}})

// Query name: AuditDeviceFunnel
LoadCsv("device_funnel_performance.csv", {{"device_category", type text}, {"stage", type text}, {"stage_order", Int64.Type}, {"ordered_sessions", Int64.Type}, {"ordered_unique_users", Int64.Type}, {"conversion_from_product_view_rate", type number}, {"step_conversion_rate", type number}, {"abandoned_sessions", Int64.Type}, {"step_abandonment_rate", type number}, {"product_view_denominator", Int64.Type}, {"previous_stage_denominator", Int64.Type}, {"stage_label", type text}})

// Query name: AuditDailyTrends
LoadCsv("daily_conversion_trends.csv", {{"entry_date", type date}, {"stage", type text}, {"stage_order", Int64.Type}, {"ordered_sessions", Int64.Type}, {"ordered_unique_users", Int64.Type}, {"conversion_from_product_view_rate", type number}, {"step_conversion_rate", type number}, {"abandoned_sessions", Int64.Type}, {"step_abandonment_rate", type number}, {"product_view_denominator", Int64.Type}, {"previous_stage_denominator", Int64.Type}, {"stage_label", type text}})

// Query name: Attribution
LoadCsv("acquisition_completeness.csv", {{"activity_date", type date}, {"event_denominator", Int64.Type}, {"missing_events", Int64.Type}, {"missing_rate", type number}, {"attribution_field", type text}, {"available_events", Int64.Type}, {"completeness_rate", type number}})

// Query name: QualityIndicators
LoadCsv("quality_indicators.csv", {{"indicator", type text}, {"value", Int64.Type}, {"denominator", Int64.Type}, {"status", type text}, {"definition", type text}, {"scope", type text}})

// Query name: DataCoverage
LoadCsv("data_coverage.csv", {{"date", type date}, {"extracted_events", Int64.Type}, {"is_analysis_date", type logical}})

// Query name: AuditWindowKpis
LoadCsv("window_kpis.csv", {{"dataset_id", type text}, {"source_kind", type text}, {"analysis_start", type date}, {"analysis_end", type date}, {"event_count", Int64.Type}, {"unique_users", Int64.Type}, {"window_active_sessions", Int64.Type}, {"entry_cohort_sessions", Int64.Type}, {"product_view_sessions", Int64.Type}, {"ordered_purchase_sessions", Int64.Type}, {"product_view_to_purchase_rate", type number}, {"potentially_incomplete_cohort_sessions", Int64.Type}})

// Query name: CohortSessions
LoadCsv("cohort_sessions.csv", {{"device_category", type text}, {"view_item", Int64.Type}, {"add_to_cart", Int64.Type}, {"begin_checkout", Int64.Type}, {"purchase", Int64.Type}, {"entry_date", type date}, {"first_date", type date}, {"last_date", type date}, {"observed_dates", Int64.Type}, {"left_context_edge", type logical}, {"right_context_edge", type logical}, {"potentially_incomplete", type logical}, {"crosses_calendar_date", type logical}, {"user_key", Int64.Type}, {"session_key", Int64.Type}})

// Query name: UserActivity
LoadCsv("user_activity.csv", {{"activity_date", type date}, {"user_key", Int64.Type}})

// Query name: SessionActivity
LoadCsv("session_activity.csv", {{"activity_date", type date}, {"session_key", Int64.Type}})

