import holoviews as hv
from holoviews import opts, dim
hv.extension('bokeh')
from bokeh.plotting import show
import pandas as pd
from visualize import CMAP
from error import IGNORE_ERR

IGNORE_SMALLER_VALUES = 0

def sankey(collector, outpath, evaluation, savepdf):
	steps = collector.classifiers()
	data_1, data_2 = collector.classes()

	print("\n\n\nCorrelation Matrix (Sankey)\n", steps)
	global cc
	global save_plot
	
	failures_1 = []
	failures_2 = []
	for k,t in data_1.items():
		if not k in data_2:
			continue
		if t.error_type() in IGNORE_ERR:
			continue
		e_t = t.error_type()
		q = data_2[k]
		if q.error_type() in IGNORE_ERR:
			continue
		e_q = q.error_type()+ " "
		failures_1.insert(0, e_t)
		failures_2.insert(0,e_q)
		
	n = len(failures_1)
	if n == 0 or len(failures_2) == 0:
		print("sankey diagram cannot be generated, no valid data")
		return evaluation

	# create a df from the data
	df_links = pd.DataFrame([failures_1, failures_2], steps).T
	df_links = df_links.groupby(steps).apply(len)

	# convert the groupby into a dataframe
	df_links = df_links.to_frame().reset_index()

	# rename the 0 column with value
	df_links.rename(columns = {0:"value"}, inplace = True)
	df_links = df_links[df_links.value > IGNORE_SMALLER_VALUES]

	totals_t = {}
	totals_q = {}
	for index, row in df_links.iterrows():
		step_1 = row[steps[0]]
		v = totals_t.get(step_1,0)
		totals_t[step_1] = v + row.value
		step_2 = row[steps[1]]
		v = totals_q.get(step_2,0)
		totals_q[step_2] = v + row.value

	for index, row in df_links.iterrows():
		v = totals_t[row[steps[0]]]
		q = v*100/n
		if q < 1:
			df_links.at[index,steps[0]] = 'other'
		v = totals_q[row[steps[1]]]
		q = v*100/n
		if q < 1:
			df_links.at[index,steps[1]] = 'other '
	
	print(df_links)
	df_links = df_links.groupby(steps).agg({'value': 'sum'}).apply(lambda x: x*100/n)
	print(df_links)
	evaluation["matrix"] = df_links

	value_dim = hv.Dimension('value', unit='%', value_format=lambda x: '%.1f' % x)
	sankey = hv.Sankey(df_links, kdims=steps, vdims=value_dim)

	hv.extension('matplotlib')
	sankey.opts(opts.Sankey(cmap=CMAP,labels='index', edge_color=dim(steps[0]).str(),node_color=dim('index').str(), label_text_font_size="xx-large", label_position="outer", node_width=50, show_values=True, fig_size=160))
	if savepdf:
		hv.Store.renderers['matplotlib'].save(sankey, outpath, 'pdf')
	else:
		show(hv.render(sankey, "bokeh", dpi = 500))

	
	return evaluation