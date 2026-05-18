TypeError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/rcdef/streamlit_app.py", line 3387, in <module>
    main()
    ~~~~^^
File "/mount/src/rcdef/streamlit_app.py", line 3332, in main
    df, status = build_master_dataset(year)
                 ~~~~~~~~~~~~~~~~~~~~^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/caching/cache_utils.py", line 280, in __call__
    return self._get_or_create_cached_value(args, kwargs, spinner_message)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/caching/cache_utils.py", line 325, in _get_or_create_cached_value
    return self._handle_cache_miss(cache, value_key, func_args, func_kwargs)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/streamlit/runtime/caching/cache_utils.py", line 384, in _handle_cache_miss
    computed_value = self._info.func(*func_args, **func_kwargs)
File "/mount/src/rcdef/streamlit_app.py", line 1534, in build_master_dataset
    main_df = calculate_rcdef(main_df)
File "/mount/src/rcdef/streamlit_app.py", line 1175, in calculate_rcdef
    rcdef_vals[valid] += df.loc[valid, comp]
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/generic.py", line 12338, in __iadd__
    return self._inplace_method(other, type(self).__add__)  # type: ignore[operator]
           ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/generic.py", line 12328, in _inplace_method
    result = op(self, other)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/ops/common.py", line 85, in new_method
    return method(self, other)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arraylike.py", line 190, in __add__
    return self._arith_method(other, operator.add)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/series.py", line 6751, in _arith_method
    return base.IndexOpsMixin._arith_method(self, other, op)
           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/base.py", line 1644, in _arith_method
    result = ops.arithmetic_op(lvalues, rvalues, op)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/ops/array_ops.py", line 279, in arithmetic_op
    res_values = op(left, right)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/arrow/array.py", line 845, in __array_ufunc__
    result = super().__array_ufunc__(ufunc, method, *inputs, **kwargs)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/base.py", line 2705, in __array_ufunc__
    result = arraylike.maybe_dispatch_ufunc_to_dunder_op(
        self, ufunc, method, *inputs, **kwargs
    )
File "pandas/_libs/ops_dispatch.pyx", line 113, in pandas._libs.ops_dispatch.maybe_dispatch_ufunc_to_dunder_op
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/ops/common.py", line 85, in new_method
    return method(self, other)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arraylike.py", line 194, in __radd__
    return self._arith_method(other, roperator.radd)
           ~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/arrow/array.py", line 1091, in _arith_method
    result = self._evaluate_op_method(other, op, ARROW_ARITHMETIC_FUNCS)
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/arrays/arrow/array.py", line 1002, in _evaluate_op_method
    raise TypeError(
        self._op_method_error_message(other_original, op)
    ) from err
