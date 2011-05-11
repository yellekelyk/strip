module FlopSync #(width=1, DEFAULT=0)
   (input clk,
    input reset,
    input en,
    input [width-1:0] d,
    output logic [width-1:0] q);

   always @(posedge clk)
     if (reset)
       q <= #1 DEFAULT;
     else
       if (en)
	 q <= #1 d;
   
endmodule // FlopSync
