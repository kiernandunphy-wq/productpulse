# Three-page report specification

Build a 16:9 canvas with consistent title, scope subtitle, aligned cards and a bottom methodology strip. This is a design specification; it is not a rendered or verified report.

## Page 1 — Executive Overview

Top: **ProductPulse | Ecommerce funnel**, subtitle **Real GA4 public sample • Jan 1–7, 2021 • Observed-entry funnel with adjacent-date context**. Add a date-range slicer and reset-filters bookmark. No device slicer on this page, so the calendar cards and cohort cards do not imply a shared device scope.

First row: five cards for Total Events, Unique Active Users, Eligible Active Sessions, Entry Cohort Sessions and Product View to Purchase Conversion. Use explicit titles **Window-active eligible sessions** and **Entry-cohort sessions**. Tooltips describe their different date scopes.

Second row: left 55% width horizontal ordered bar chart using DimStage[stage_label] and Stage Sessions, sorted stage_order ascending; show counts and tooltips for Stage Conversion from Product View, Step Conversion, Abandoned Sessions and Step Abandonment. Bars make the differing counts easier to read than area shapes. Right: line chart of DimDate[date] and Product View to Purchase Conversion, with Product View Sessions and Ordered Purchase Sessions in the tooltip. Rates recompute under date filters from numerators and denominators.

Bottom: three fixed-window finding cards/text blocks: **81.15% drop from view to cart**, **91 ordered purchase sessions from 3,942 viewing sessions**, **26.76% of calendar events lack source attribution**. Header says **Full-window findings, unaffected by slicers**. Keep findings factual; do not call the drop a proven UX issue. Display a note that observed context improves boundary handling without proving full journeys.

## Page 2 — Customer Behavior

Top slicers: date range and **Entry device — cohort visuals only**, with reset bookmark. No campaign, retention or engaged-session slicer: these data do not support them. No stage slicer shared with KPI cards.

Upper left: device clustered bar chart for Product View to Purchase Conversion, DimDevice[device_category] as axis. Tooltips include cohort count, viewing denominator, purchases and incomplete count; show purchase count labels in an adjacent table. Tablet has only four ordered purchases; do not rank it as a proven winner.

Upper right: stage abandonment bar chart using DimStage labels and Step Abandonment; omit the first-stage blank. Include Abandoned Sessions and Previous Stage Sessions tooltips. Device/date filters affect both upper visuals. Device chart cross-filtering must not reach lower activity/attribution visuals: use Edit interactions > None for these targets.

Lower left: daily active users line chart using DimDate and Unique Active Users; optional second small chart for Total Events. Title **All devices — calendar activity**. This is observed activity, not GA4 engaged sessions, engagement rate or average duration. No such unsupported metric should appear.

Lower right: two horizontal bars for Attribution Completeness Rate with Attribution[attribution_field] on axis; tooltip shows Missing Attribution Events, Attribution Event Denominator and Attribution Missing Rate. Title **All devices — first-user attribution completeness**. Date filters apply; device interactions are disabled. Source and medium totals remain separate.

## Page 3 — Data Quality & Methodology

No date/device slicers on this page. Top fixed-window cards: recorded reconciliation status, 4 potentially incomplete cohort sessions, missing source 26.76%, missing medium 14.67%. QualityIndicators rows show recorded checks, not a live cloud connection status. Packaging validation is in manifest.json; do not claim Desktop or DAX validation until manual acceptance passes.

Left: coverage table from DataCoverage for all nine source dates, extracted_events and is_analysis_date. Distinguish two context dates using text badges in addition to color. Main window has 245,209 events; context-inclusive export has 310,947.

Center: quality table with indicator, value, denominator, status and definition. Counts include zero missing user/session rows and zero projected duplicates; sample obfuscation still limits inference.

Right: concise methodology text: composite user/session identity, strict view → cart → checkout → purchase order, equal timestamps cannot establish a step, earliest-event device policy, observed-entry date policy, four right-context flags included. Show the boundary sensitivity (2.28% excluding four flagged sessions) as a secondary fixed-window note. It does not replace the established inclusive 2.31% metric.

Footer: pseudonyms are not people; purchaser reach is not orders or full funnels; source/medium are first-user acquisition; no causal claims; no revenue, retention or experiment findings. Link to portfolio summary and data dictionary in the published description once a real report exists.

## Accessibility and presentation

Use white `#FFFFFF` background, dark navy `#172B4D` text, blue `#005A9C` primary bars, dark orange `#A64500` warnings and dark teal `#006B5E` success. Avoid encoding success/failure only with red/green. Use neutral gray grid lines and at least 12 pt labels, 16 pt card titles and 24+ pt page titles. The optional `theme.json` supplies base colors; verify actual contrast in Desktop, including selected/highlighted states.

Show counts alongside percentage values, include denominator tooltips, keep chart titles specific to date/device scope, and avoid truncated stage labels. Set alt text describing the metric and scope, logical tab order from slicers to cards to visuals, and test high-contrast mode and keyboard-only navigation. Microsoft's [accessibility guidance](https://learn.microsoft.com/en-us/power-bi/create-reports/desktop-accessibility-creating-reports) covers alt text and navigation. Do not use decorative images that compete with metric labels.
