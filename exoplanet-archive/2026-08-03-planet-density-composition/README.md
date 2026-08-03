# What are exoplanets probably made of? A density-based sort

I pulled real mass and radius values for 6,253 confirmed exoplanets from the NASA Exoplanet Archive and computed each one's bulk density the same way you'd compute it for any object: mass divided by volume. Then I sorted every planet into one of four composition classes using real, measured solar-system densities as dividing lines: pure iron (~8.0 g/cm^3) at the dense end, Earth's own density (5.51 g/cm^3) for rocky worlds, Neptune's density (1.64 g/cm^3) for ice-and-gas-rich planets, and Jupiter's density (1.33 g/cm^3) for hydrogen/helium-dominated giants.

The split: 2,020 planets (32%) land in the "volatile/water-rich" band (median density 2.17 g/cm^3), 2,000 (32%) look "rocky, Earth-like" (median density 4.50 g/cm^3), 1,576 (25%) are "H/He-dominated" gas giants (median density 0.63 g/cm^3), and 657 (10%) are dense enough to call "iron-rich" (median density 10.85 g/cm^3). That so much of the sample sits in the puffier, larger-radius bins reflects a real detection-bias effect layered on top of any true compositional trend: Neptune- and Jupiter-sized planets are simply easier to detect by transit and radial velocity than small rocky ones, so this split describes the discovered sample, not necessarily the true occurrence rate of each planet type in the galaxy.

A robustness check shifting every density boundary down by 20% left the ranking of class sizes unchanged, which is reassuring for the qualitative picture. The real limitation is that density alone can't fully separate a genuinely water-rich planet from a rocky planet wearing a puffy hydrogen envelope of similar bulk density -- both are real, physically distinct possibilities that this simple classification can't tell apart.

The plot shows a real mass-radius diagram with the four constant-density reference lines overlaid, plus a bar chart of the class counts.

**What I'd look at next:** replace the constant-density reference lines with actual two- or three-layer interior-structure models (using a real equation of state), since true composition curves flatten at high mass due to self-compression, and the fixed-density anchors used here likely mis-rank the most massive planets in the sample.

**Citation:** NASA Exoplanet Archive, Caltech/NASA Exoplanet Exploration Program: https://exoplanetarchive.ipac.caltech.edu/docs/TAP/usingTAP.html
