# ORBIT DELTA: judge demonstration script

Allow about 13 minutes for the main demonstration, including clicks and loading. Rehearse once and shorten it if the organisers give you a smaller slot. The questions at the end are outside that time. Read the spoken paragraphs aloud. Text in square brackets is an action for the presenter.

## Before the judges arrive

Open these pages in separate tabs on the same running application:

1. `/orbit`: image comparison and synthetic scenarios.
2. `/orbit/water`: NASA observations and experimental water anomaly models.
3. `/orbit/thermal`: stored thermal-source classifications.

Start with the River overflow scenario at its final frame and the default detection threshold of 0.20. Keep the Unchanged control scenario ready for the reliability check. The scenario names and all measurements should come from the current screen.

On Water Watch, choose Nagarjuna Sagar and select 17 May 2026. With the current 89-observation dataset, focus the Observation date slider, press End, then press Left Arrow four times. Confirm the displayed date before presenting. Its preceding usable observation is 17 April 2026. Pause playback before inspecting results.

Select one thermal source before presenting. Choose a point whose satellite photograph loads. Read the stored class, date range and detection count from that selected source. Do not substitute a different source's numbers.

The public showcase opens without login. Internet is needed for Esri imagery; the bundled NASA observations and model evidence are local. Keep the 25-second video available as a backup introduction. Rehearse the live flow once.

## 0:00 to 1:00: introduce the problem

[Open `/orbit`. Keep the comparison visible.]

"Our project is ORBIT DELTA. It helps someone inspect changes in satellite images and decide what needs a closer check.

A satellite image can show water, vegetation, buildings or exposed land. But one image does not tell us what changed. We need to compare observations from different dates, locate the changed areas and explain what the evidence can support.

That is the problem we chose from Track 05. Our prototype has an image comparison workspace and a water-monitoring page built on real NASA observations. We also retain the thermal-monitoring view from our earlier project as supporting context.

I will first show how we inspect a change, then show the same investigation using real water observations."

## 1:00 to 3:00: compare images and inspect regions

[Choose River overflow. Drag the before/after divider slowly.]

"These first images are synthetic. We included them so we can test a known change and demonstrate the complete workflow reliably.

The divider lets us compare the same location before and after the change. When I move it, you can see where the image has changed."

[Turn Change regions off, then on. Select a numbered region.]

"The outlines show the regions that our analysis retained. I can select one region and inspect its changed-pixel count in the evidence panel.

The percentage tells us how much of the compared image contains retained change. A pixel is one small cell in the image. We calculate area when we know how much ground each pixel covers. For these synthetic examples, the scale is an assumption and the screen labels it that way.

For uploaded images, we accept aligned 512 by 512 PNG or JPEG pairs. Aligned means that both images show the same ground in the same position. If the user does not know the ground scale, we keep the result in pixels and percentage."

[Move Detection threshold slightly toward Less sensitive. Wait for analysis.]

"This control changes how much visual difference is needed before we keep a region. A lower threshold can reveal smaller differences, but it can also include more noise.

When the images or detection settings change, the old assessment is cleared. That keeps the explanation tied to the current result."

## 3:00 to 4:30: explain the assessment and show the control

[Click Generate assessment. Point to Possible explanation and Next verification.]

"We separate what the program measured from what might explain it.

The measured result is the location and amount of visible change. The explanation is a hypothesis. Water expansion, for example, needs further checks before we call it a flood or assign a cause.

The current public demo generates its report from the measured regions. The project also supports Gemini for paired-image interpretation when configured. The local report remains available if that service fails.

The report points the reviewer toward the next check, such as rainfall records, reservoir operations or later images."

[Download Assessment JSON and Annotated image. Then choose Unchanged control.]

"The reviewer can download the measurements and an annotated image.

This control uses identical images. It should produce zero retained change. This is one of our checks that the detector responds to the image evidence."

[Optional, if time permits: choose Land excavation, then briefly play and pause scenario replay.]

"The same image comparison process also works on a land-disturbance example. These replay frames are labelled simulation. They are not additional satellite observations or a forecast."

## 4:30 to 6:00: introduce the real NASA dataset

[Switch to `/orbit/water`. Select Nagarjuna Sagar.]

"The water page uses real cached NASA OPERA DSWx-HLS observations. NASA provides a classification for each 30-metre cell. We use the cells classified as open water to measure the visible water surface.

We collected observations for selected parts of Hirakud, Nagarjuna Sagar and Sardar Sarovar. These are fixed study areas, rather than the whole reservoirs.

We chose three locations to keep this prototype manageable. NASA's dataset covers many more locations. These three were not selected because we had confirmed a problem at them.

After our quality filter, the app has 341 usable observations. We require at least 95 percent of the study area to contain valid classifications before accepting a date. Clouds and missing data reduce the number of usable dates.

The blue and teal image here is a water-classification map. Blue means open water, teal means partial water, tan means non-water, and dark areas contain invalid observations."

## 6:00 to 7:45: demonstrate a real water change

[Select 17 May 2026. Open Before / after. Drag the divider.]

"I am comparing 17 April with 17 May 2026 at Nagarjuna Sagar. These are actual usable observation dates in our dataset.

The selected observation contains about 115.86 square kilometres of classified open water within our study area."

[Switch to Change map. Select a changed region. Point to Measured change.]

"Across pixels that are valid on both dates, the comparison measures about 26.25 square kilometres of open-water loss and 0.32 square kilometres of gain.

For this change map, blue means gain and orange means loss. The colour meaning is different from the water-classification image.

We compare only cells that have valid data on both dates. A cloud or missing observation should not be counted as disappearing water. This also means the gain and loss totals may differ from simply subtracting the two whole-image water areas.

These measurements tell us where NASA's classification changed. A reviewer still needs to check whether the difference reflects a physical water change or a classification error."

[Briefly play the observation history, then pause.]

"The timeline moves through the dates we have. It does not create observations between satellite acquisitions."

## 7:45 to 10:00: explain what the model detects

[Point to the observed-area chart, seasonal baseline, score and threshold.]

"Water area can change with the season, so a difference between two images is not enough to call it unusual.

We fit a seasonal baseline from the training history. The dashed line shows the expected pattern from that baseline. The solid line shows the observed water area.

For each reservoir segment, we trained an Isolation Forest. That is a machine-learning model that looks for unusual combinations of measurements.

It considers how far the water area is from the seasonal baseline, how large it is compared with the training history, its recent rate of change and how much it has varied recently.

On 17 May, the Nagarjuna Sagar model produces a score of about 0.643. Its alert threshold is about 0.565, so this observation is flagged for review. That score measures unusual behaviour. It is not a percentage chance of a flood.

We used observations through 2024 for training,2025 for validation and the available 2026 dates for testing. We kept the dates in order.

All three models are labelled experimental because they fall short of our planned minimum training history. We also do not have independently confirmed event labels, so we cannot claim a validated flood-detection accuracy or warning lead time.

The useful result today is a dated observation, a visible region to inspect and a reason to check it."

## 10:00 to 11:00: show the thermal-source context

[Switch to `/orbit/thermal`. Select the prepared source. Toggle one class filter off and on.]

"This is the thermal-monitoring part of our earlier project. We are disclosing that reuse. For this hackathon, we extended that platform with image change inspection and water anomaly analysis.

This page contains stored thermal-source classifications. I can filter by class, select a source and inspect its recorded detections and dates.

The photograph below the details provides satellite context around the selected source. It comes from Esri World Imagery. It is a composite and may not match the detection date.

The thermal model and the water model do different jobs. One classifies thermal sources. The other flags unusual patterns in measured surface-water area."

[If a spread circle is visible, add:]

"This spread circle is an illustrative estimate based on area growth. We have not validated it as a fire forecast."

## 11:00 to 12:30: connect the demo to the problem statement

[Return to the image comparison or water page, with a selected region visible.]

"For Track 05, we can demonstrate image comparison, marked change regions and an assessment that refers to the evidence. The upload workspace handles a general image pair, and the water page adds a dated observation history.

The natural-versus-human distinction needs care. Appearance can suggest a possible explanation, but an image difference alone does not establish cause. A burn scar, for example, does not tell us who or what started the fire.

Our reporting supports natural-like, human-like and uncertain hypotheses. In the current public demo, the report keeps the cause uncertain and gives a verification action. We would need stronger contextual evidence and independent validation before treating cause classification as reliable.

The interface runs in React with MapLibre. FastAPI handles the requests. OpenCV and scikit-image measure image changes. The water model uses scikit-learn. The public demonstration runs from bundled evidence without a database or ingestion services."

## 12:30 to 13:00: close with the result

[Keep a selected change region and its assessment visible.]

"ORBIT DELTA gives a reviewer a place to start: what changed, where it changed and what to check next.

We can show that process with controlled test images, repeat it on real NASA water observations and export the evidence for further review. That is the working prototype we are presenting today."

## Judge questions: short answers

### What exactly is an anomaly?

"It is a measurement or combination of measurements that is unusual compared with the pattern learned for that site. It is an observation to review. It does not confirm a disaster."

### Did you train a model to recognise water in satellite photos?

"NASA already supplies the water classifications. We trained a separate Isolation Forest on measurements derived from those classifications. Our model looks for unusual water-area patterns."

### Can it predict a flood, storm or water outage?

"The current prototype detects unusual observed surface-water patterns. Forecasting those events would need additional inputs, such as rainfall forecasts, gauges, catchment information and reservoir-operation records, followed by validation against real events."

### Does water-area loss tell you how many litres were lost?

"We measure visible surface area. To estimate volume, we would also need water levels and information about the reservoir's shape and depth."

### Can it say whether a change is natural or human-made?

"It can present an appearance hypothesis when supported by evidence. The current public report uses uncertain cause. Rainfall, reservoir releases and withdrawals can produce similar visible changes, so cause needs further evidence."

### How accurate is it?

"We have checks for the measurements and the software. We do not yet have validated event accuracy, because we lack independently confirmed flood or shortage labels. The experimental status remains visible in the app."

### Why use only three locations?

"That was our prototype scope. Each site needs its own collected history, quality checks and model evaluation. The source dataset covers many more places."

### Is it live?

"This version replays cached real observations on their actual dates. It does not automatically fetch new observations. The collection scripts provide a path to adding newer data."

### What happens when there are clouds?

"We exclude invalid cells, accept dates only when they pass the coverage filter, and measure change only where both dates have valid observations. Classification errors can still remain."

### Why do some screens use synthetic images?

"They give us controlled examples, including an unchanged pair, for testing the image-comparison workflow. We label them synthetic. The water page uses separately labelled real NASA observations."

### Is the AI report inventing measurements?

"The image-processing code calculates the measurements. A generated explanation must refer to those measured regions. The public version uses a deterministic local report, and the optional Gemini report has structure and region-reference checks."

### What was built before this hackathon?

"The thermal-monitoring platform existed before this event. We reused it and extended it with image change comparison, marked regions, assessments and the water observation workflow. We will follow the organisers' rules on prior work."

### What makes this useful beyond a graph?

"A flagged point on a graph leads to the source date, the image comparison and the affected region. The reviewer can inspect the evidence and export it rather than relying on the score alone."

### What is your next technical step?

"We need more usable history and independently confirmed events. We would then test the alerts against those events and add rainfall or gauge evidence where it helps explain the change."

## If the live demo has a problem

If the satellite photograph fails: "The external imagery provider is unavailable. The cached NASA classification images and local measurements still work."

If a report service fails: "The local report uses the measured regions, so we can continue inspecting and exporting the result."

If the deployed site does not open: switch to the local showcase. If that also fails, use the saved launch video and exported images, and tell the judges that you are showing recorded output.

## Words to keep straight

Observation: a satellite acquisition on a stated date.
Water classification: NASA's label for each ground cell.
Change: a difference between two observations.
Seasonal baseline: an expected annual pattern fitted from training observations.
Anomaly: an unusual measurement pattern that needs review.
Hypothesis: a possible explanation that still needs evidence.
Forecast: a statement about a future event. The current water prototype does not produce one.

The displayed experimental-model warning, cached-data label and synthetic-scenario label are part of the explanation. Keep them visible.
