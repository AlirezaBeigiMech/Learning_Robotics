## Frames of a mobile robot

Navigation software (Nav2, Chapter 6) expects every mobile robot to use the same frame names and axes.
These are defined in **REP 103** (units, x forward / y left / z up) and **REP 105** (frame names):

```
map ─▶ odom ─▶ base_footprint ─▶ base_link ─▶ wheels, sensors…
```

* `base_footprint`: the robot's projection on the **ground** (z = 0). 2D planners use it.
* `base_link`: rigidly attached to the chassis. Here it sits at **wheel-axle height**, so the wheels
  attach at z = 0 relative to it.
* `odom` and `map` come later, from odometry and localisation (Chapters 6 and 11).

A robot whose wheels float above the ground, or sink below it, makes a physics simulator misbehave and
confuses anyone reading TF. The final submission checks ground contact from your model.
