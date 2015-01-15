	var asInitVals = new Array();
			$(document).ready(function()   //jquery
			{
				var tagArr = ['2-sat', 'bit', 'adhoc', 'aho-corasick', 'articulation-point', 'backtracking', 'bellman-ford', 'bfs', 'biconnected-comp', 'big-integer', 'binary-numbers', 'binary-search', 'binary-tree', 'binomial', 'bipartite', 'bitmasking', 'bitwise', 'bridges', 'brute-force', 'burnside', 'chinese-remainder', 'combinatorics', 'complete-search', 'convex-hull', 'data-structure', 'decomposition', 'deque', 'dfs', 'dijkstra', 'discretization', 'disjoint-set', 'divide-and-conquer', 'dp', 'enumeration', 'euler-tour', 'expectation', 'exponentiation', 'factorial', 'factorization', 'fft', 'fibonacci', 'floyd-warshall', 'game-theory', 'gauss-elim', 'gcd', 'geometry', 'grammar-parsing', 'graphs', 'greedy', 'hashing', 'heaps', 'heavy-light', 'heuristic', 'hungarian', 'impartial-game', 'implementation', 'inclusion-exclusion', 'inversions', 'kd-tree', 'kmp', 'kruskal', 'lca', 'lcp', 'line-sweep', 'linear-programming', 'link-cut-tree', 'matching', 'maths', 'matrix-expo', 'max-independent-set', 'maxflow', 'meet-in-middle', 'memoization', 'miller-rabin', 'min-cost-flow', 'mincut', 'modulo', 'mst', 'newton-raphson', 'number-theory', 'offline-query', 'order-statistic', 'palindrome', 'permutation', 'persistence', 'pigeonhole', 'polygons', 'precision', 'prefix-sum', 'preprocessing', 'prim', 'prime', 'probability', 'queue', 'rabin-karp', 'recurrence', 'recursion', 'regex', 'scc', 'segment-tree', 'shortest-path', 'sieve', 'sliding-window', 'sorting', 'sparse-tables', 'splay-tree', 'sprague-grundy', 'sqrt-decomposition', 'stable-marriage', 'stack', 'string', 'suffix-array', 'suffix-auto', 'suffix-trees', 'ternary-search', 'topological-sort', 'treap', 'tree-dp', 'trees', 'trie', 'two-pointers', 'union-find', 'vertex-cover', 'xor', 'zero-sum-game'];
			  	//tags start

			  	//preven form submit on enter in tag input textbox in modal
			  	$('#form-tag-input').keydown(function(event){
			  		if(event.keyCode == 13) {
			  			event.preventDefault();
			  			return false;
			  		}
			  	});
			  	var my_tags = $('#form-tag-input').tags
			  	(
			  	{
			  		suggestions : tagArr,
			  		restrictTo : tagArr,
			  		caseInsensitive : true
			  	}
			  	);

				//tags end

				//update logic
				$(".update").click
				(
					function()
					{
						var row = $(this).parent().parent();
						if(!login)
						{
							alert('Please login to continue');
							return;
						}
						var probid = row.attr('id');  //HTML STRUCTURE WARNING
						$("#static-pcode").text(probid); //add pcode static text
						$("#star-raty").raty('reload'); //reload raty
						//clear radios
						$('#inlineradio1').attr('checked', false);
						$('#inlineradio2').attr('checked', false);
						//clear tags
						while(my_tags.getTags().length > 0)
						{
							my_tags.removeLastTag();
						}
						$('#form-tag-input').css("padding-bottom", "0px"); //having large input area without this 
						$('#myModal').modal('show');
					}
					);
				//todo logic
				$(".button-data").on("click", ".todo", 	function()
					{
						var probid = $(this).parent().parent().attr('id');
						var par = $(this).parent();
						$.ajax
						(
						{
							url : "todo",
							data : {id : probid},
							type : "POST",
							dataType : "json",
							success : function(json)
							{
								if(!json.fail)
								{
									alert(json.success_msg + "hello");
									// --> \ is for multiline string in js
									par.html('<button type="button" class="btn btn-danger un-todo "> \
															<span class="glyphicon glyphicon-minus"></span>Todo \
															</button>');
								}
								else
								{
									alert('Sorry your request failed. Reason : ' + json.fail_msg);
								}
							},
							error : function(xhr, status)
							{
								alert("Sorry your request failed. Please contact the site admin");
							}
						}
						)
					}
				);
				//on() also listens for changes in class and dynamically binds events, unlike click which binds events only once
				//un-todo logic
				$(".button-data").on("click", ".un-todo", 	function()
					{
						var probid = $(this).parent().parent().attr('id');
						var par = $(this).parent();
						$.ajax
						(
						{
							url : "untodo",
							data : {id : probid},
							type : "POST",
							dataType : "json",
							success : function(json)
							{
								if(!json.fail)
								{
									alert(json.success_msg);
									// --> \ is for multiline string in js
									par.html('<button type="button" class="btn btn-success todo "> \
															<span class="glyphicon glyphicon-plus"></span>Todo \
															</button>');
								}
								else
								{
									alert('Sorry your request failed. Reason : ' + json.fail_msg);
								}
							},
							error : function(xhr, status)
							{
								alert("Sorry your request failed. Please contact the site admin");
							}
						}
						)
					}
				);
				$('#make-update').click
				(
					function()
					{
						var pcode = $('#static-pcode').text();
						var tags = JSON.stringify(my_tags.getTags());
						var rating = $('#star-raty').raty('score');
						var yes_radio = $('#inlineradio1').is(':checked');
						//no radio is insignificant
						// alert(pcode);
						mydata = {id:pcode, tags : tags, rating:rating, yes_radio:yes_radio};
						// alert(JSON.stringify(mydata));
						//submit data to server
						$.ajax
						(
						{
							url : "dataupdate",
							data : {id:pcode, tags : tags, rating:rating, yes_radio:yes_radio},
							type : "POST",
								dataType : "json", //return type
								success : 	function(json)
								{
									if(!json.fail)
									{
										alert('Your changes were saved');
										// alert(JSON.stringify(json));
										$('#'+pcode).html(json.updated_row);	
									}
									else
									{
										alert('Sorry your request failed. Reason : ' + json.fail_msg);
									}
								},
								error : function(xhr, status)
								{
									alert("Sorry your request failed. Please contact the site admin");
								},
								complete : function(xhr, status)
								{
												//close modal
												$('#myModal').modal('hide');
											}
										}
										);
					}
					);
				//datatable related
				var oTable = $('#mytable').dataTable( {
					"iDisplayLength": 25,
					"oLanguage": {
						"sSearch": "Search all columns:"
					}
					,'bAutoWidth' : false 
				} );
				$("thead input").keyup( function () {
					/* Filter on the column (the index) of this element */
					oTable.fnFilter( this.value, $("thead input").index(this) );
				} );
				/*
				 * Support functions to provide a little bit of 'user friendlyness' to the textboxes in 
				 * the footer
				 */
				 $("thead input").each( function (i) {
				 	asInitVals[i] = this.value;
				 } );

				 $("thead input").focus( function () {
				 	if ( this.className == "search_init" )
				 	{
				 		this.className = "";
				 		this.value = "";
				 	}
				 } );
				 $("thead input").blur( function (i) {
				 	if ( this.value == "" )
				 	{
				 		this.className = "search_init";
				 		this.value = asInitVals[$("thead input").index(this)];
				 	}
				 } );
				//end datatable related

				//raty
				$('#star-raty').raty
				(
				{ 
					path: 'images/'
				}
				);
				//raty end	
			} );