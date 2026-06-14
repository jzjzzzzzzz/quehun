# Learned Discard Templates

River tiles have a different perspective from hand tiles. The analyzer learns
these templates automatically when a stable, high-confidence hand changes from
14 tiles to 13 tiles and exactly one new self-discard contour appears.

Templates are stored by canonical tile label. Learned templates are used for
all four discard rivers after applying the configured rotation.
