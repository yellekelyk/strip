module CapQueue #(parameter width=8, depth=4)
   (input clk,
    input reset,
    input enq,
    input deq,
    input [width-1:0] i,
    output logic full,
    output logic empty,
    output [width-1:0] o,
    output logic [utils::clog2(depth+1)-1:0] capacity);

   parameter clogDepth = utils::clog2(depth);


   
   logic [width-1:0] 			     entry [depth-1:0];
   

   // read from head address, write to tail address
   logic [clogDepth-1:0] 		     head, tail, nextHead, nextTail;

   
   int 					     unsigned depthM1 = depth -1;
   
   wire 			   incTail;
   wire 			   incHead;
   wire 			   bypass;

   
`ifdef BYPASS
   assign empty  = (capacity == depth) && !enq;
   assign full   = (capacity == 0    ) && !deq;
   assign bypass = (capacity == depth) && enq && deq;

   // write state iff we have space, and we're not bypassing
   assign incTail = enq && (!bypass) && !(capacity == 0);

   // read state iff we have stuff to read and we're not bypassing
   assign incHead = deq && (!bypass) && !(capacity == depth);
`else
   assign empty  = capacity == depth;
   assign full   = capacity == 0;
   assign bypass = '0;

   assign incTail = enq && (!full  || deq);
   assign incHead = deq && (!empty); 
`endif


   
   // we bypass the Q if needed
   //assign o = empty ? '0 : entry[head];
   assign o = bypass ? i : entry[head];

   
   assign nextHead = (head == depthM1[clogDepth-1:0]) ? '0 : head + 1'b1;
   assign nextTail = (tail == depthM1[clogDepth-1:0]) ? '0 : tail + 1'b1;
   
   // store data if queue isn't full OR if deq is active
   always @(posedge clk) begin: queue_data
      if (!reset && incTail)
	entry[tail] <= #1 i;
   end

   // queue capacity register tells how much space is free
   always @(posedge clk) begin: cap_logic
      if (reset)
	capacity <= #1 depth;
      else begin
	 if (incTail && !deq) begin
	    capacity <= #1 capacity - 1;
	 end
	 else begin
	    if (incHead && !enq) begin
	       capacity <= #1 capacity + 1;
	    end
	 end
      end
   end
   

   FlopSync #(.width(clogDepth)) headReg
     (.clk(clk), .reset(reset), .en(incHead), .d (nextHead), .q(head));

   FlopSync #(.width(clogDepth)) tailReg
     (.clk(clk), .reset(reset), .en(incTail), .d (nextTail), .q(tail));


endmodule // CapQueue


