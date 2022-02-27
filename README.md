# countYourBirds webserver  
Environmental changes can have different causes on local level (e.g. soil sealing) as well as on global level (e.g. climate change). To detect these changes and to find patterns in the reasons for them it is necessary to collect broad environmental data, temporally and spatially. Thereto citizens can play an essential role to collect the data. In particular, we developed a system which enables citizens to to collect this data to monitor the occurrence and distribution of birds and provides the collected data it to the public in order that both researchers and citizens can derivedrive conclusions from them.

Therefore we built a prototypical bird feeder equipped with several sensors and the infrastructure to process the data collected by the feeder.
The feeder is easy to reproduce at a reasonable price by following an open available manual describing how to handle the established hardware. This allows anyone to build the feeder on their own, enabling a large distribution at many locations. The feeder automatically detects when a bird is visiting it, takes an image of the bird, determines the species and connects the observation with environmental data like the temperature or light intensity. All the collected data are published on a developed open access platform. Incorporating other surrounding factors like the proximity of the feeder to the next forest or a large street allows it to pursue various questions regarding the occurrence of birds. One of them might ask, how does the immediate environment affect bird abundance? Or do sealed surfaces have a negative effect compared to a flowering garden?

This repository contains the code to run the webserver. 
All the collected data is send by a feeder which is based on this [repository](https://github.com/CountYourBirds/station). 
The repositories are currently still under development, the code for the operation of the feeder as well as for the web server are continuously updated. 
A corresponding manual for the operation of the system including open source instructions for building the feeder will follow soon. 

CountYourBirds is a project by a group of students at the Institute for Geoinformatics at the University of Münster. 
If you got any questions contact us via: [info@countyourbirds.org](mailto:info@countyourbirds.org).