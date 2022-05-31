# How to read behavioral snapshot figures #

## Overview column (for each mouse in figures per lab, leftmost column in figures per mouse) ##

### 1st panel from top: weight and water intake ###
Black curve and datapoints: animal's weight over time. White diamond indicates the _reference weight_ at the moment that a _water restriction_ started (indicated in Alyx). Dashed lines show 85% and 75% of this reference weight, for each period in which the animal was water restricted. If the animal was taken off water restriction (e.g. got a bottle in its cage during holidays), a new water restriction with associated reference weigth and 85%/75% lines is shown.

Colored bars: cumulative water intake per day, colors indicate the type of water. 10% sucrose is the standard water type that's earned in the behavioral task, hydrogel is used for top-up during the week (if animals don't earn their required liquids in the task), and in weekends measured water or adlib water with 2% citric acid can be given. 

### 2nd panel from top: session duration and trial count ###
For each day of the behavioral task (starting with `trainingChoiceWorld`), number of trials performed and duration of the session.

### 3rd panel from top: performance and RT ###
For each day of the behavioral task, performance (only on easy trials, i.e. 50% and 100% contrast) and median RT. We've observed that once the two 'cross over', i.e. median RT goes below accuracy, animals will become proficient at the task soon after.

### 4th panel from top: contrast/choice heatmap ###
For each day of the behavioral task (x-axis) and each contrast level (y-axis), the fraction of rightward choices. Ideal performance would be dark blue bars at the top half, and dark red bars at the bottom half. This plot is basically a flattened psychometric function into a heatmap, over days. You can see when additional, more difficult contrasts are introduced over training.
