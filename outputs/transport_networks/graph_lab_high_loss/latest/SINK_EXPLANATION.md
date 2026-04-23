# What the sink means

In these simulations, the `sink` is an absorbing target state that represents successful transport.

- It is not one more physical node of the graph.
- It is a bookkeeping state that receives population from the chosen trap site.
- When population reaches the sink, that part of the excitation is counted as a successful arrival.
- The main observable `sink efficiency` is therefore the final sink population.

This is useful because it separates three different things:

- coherent motion inside the graph;
- successful capture into the target channel (`sink`);
- unwanted dissipation into the `loss` channel.
